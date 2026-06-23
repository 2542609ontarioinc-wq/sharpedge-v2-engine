"use client";

import { useState } from "react";
import type { MLBPickDetail, MLBPlayerProp, MLBSafeZonePick, MLBSharpPick, MLBSubscriberSegment } from "@/lib/types";
import { DateSelector } from "./DateSelector";
import { formatFirstPitch } from "@/lib/format";
import { EmptyState } from "./EmptyState";
import { TeamLogo } from "./TeamLogo";
import { LiveScoreModule } from "./LiveScoreModule";
import type { LiveScore } from "@/hooks/useLiveScores";

// ─── Filter thresholds (unchanged) ──────────────────────────────────────────
const EDGE_MIN  = 3;   // min model edge % for picks that carry an edge signal
const PROB_MIN  = 65;  // min win-probability % for all pick types
const BOTD_EDGE = 5;   // BotD candidate bar: edge >= this
const BOTD_PROB = 70;  // BotD candidate bar: win prob >= this

// ─── Postponed/cancelled game detection ──────────────────────────────────────
// Mirrors POSTPONED_STATUSES in grade_mlb_picks.py / grade_mlb_prop_picks.py.
const POSTPONED_STATUS_SET = new Set(["postponed", "cancelled", "canceled", "suspended", "post"]);

function isPostponedStatus(gameStatus: string): boolean {
  const lower = gameStatus.toLowerCase().trim();
  if (POSTPONED_STATUS_SET.has(lower)) return true;
  // Handle compound MLB detailedState strings: "Postponed: Rain", "Suspended: Darkness"
  const firstWord = lower.split(/[\s:]/)[0];
  return POSTPONED_STATUS_SET.has(firstWord);
}

// Props cap per game (display only — does not affect qualifying logic)
const MAX_PROPS_PER_GAME = 2;

// ─── Client-side subscriber segment computation ──────────────────────────────
const SAFE_MARKETS = new Set(["safe_balanced", "safe_banker"]);
const GAME_MARKETS = new Set(["moneyline", "totals", "run_line"]);

function isQualified(p: MLBPickDetail): boolean {
  if (p.edgeFlag !== "REAL") return false;
  if (GAME_MARKETS.has(p.market)) {
    return (p.modelEdge ?? 0) >= EDGE_MIN && (p.calibratedConf ?? 0) >= PROB_MIN;
  }
  return SAFE_MARKETS.has(p.market);
}

function isBotD(p: MLBPickDetail): boolean {
  if (!isQualified(p)) return false;
  return GAME_MARKETS.has(p.market) &&
    (p.modelEdge ?? 0) >= BOTD_EDGE &&
    (p.calibratedConf ?? 0) >= BOTD_PROB;
}

function computeSegment(rows: MLBPickDetail[]): MLBSubscriberSegment | null {
  const graded = rows.filter((p) => p.grade === "WIN" || p.grade === "LOSS");
  if (graded.length === 0) return null;
  const wins = graded.filter((p) => p.grade === "WIN").length;
  const clvRows = graded.filter((p) => p.clv !== null);
  const unitsProfit = graded.reduce((s, p) => s + (p.unitsResult ?? 0), 0);
  const edgeRows = graded.filter((p) => p.modelEdge !== null);
  const confRows = graded.filter((p) => p.calibratedConf !== null);
  return {
    pickCount: graded.length,
    winCount: wins,
    lossCount: graded.length - wins,
    winRate: wins / graded.length,
    unitsProfit,
    roiPercent: (unitsProfit / graded.length) * 100,
    avgEdge: edgeRows.length > 0 ? edgeRows.reduce((s, p) => s + (p.modelEdge ?? 0), 0) / edgeRows.length : null,
    avgWinProb: confRows.length > 0 ? confRows.reduce((s, p) => s + (p.calibratedConf ?? 0), 0) / confRows.length : null,
    avgClv: clvRows.length > 0 ? clvRows.reduce((s, p) => s + (p.clv ?? 0), 0) / clvRows.length : null,
    clvBeatRate: clvRows.length > 0 ? clvRows.filter((p) => p.beatClose).length / clvRows.length : null,
  };
}

// ─── Unified pick shape ──────────────────────────────────────────────────────
type PickSource = "sharp" | "balanced" | "banker" | "prop";

// Three-level display hierarchy: one BotD → a few Elite → rest Strong
type SubPickTier = "Bet of the Day" | "Elite" | "Strong";

type SubPick = {
  key: string;
  gameId: string;
  gameTime: string | null;
  homeTeam: string;
  awayTeam: string;
  source: PickSource;
  label: string;
  marketLabel: string;
  edge: number | null;
  winProb: number;
  /** edge × winProb ranking score; 0 for safe-zone picks (no edge). */
  score: number;
  oddsDecimal: number | null;
  oddsAmerican: number | null;
  tier: SubPickTier;
  playerName?: string;
};

// ─── Market labels ────────────────────────────────────────────────────────────
const PROP_LABELS: Record<string, string> = {
  strikeouts:    "Strikeouts",
  outs_recorded: "Outs Recorded",
  earned_runs:   "Earned Runs",
  hits_allowed:  "Hits Allowed",
  walks:         "Walks",
  h_r_rbi:       "H+R+RBI",
};

const GAME_MARKET_LABELS: Record<string, string> = {
  moneyline: "Moneyline",
  totals:    "Totals",
  run_line:  "Run Line",
};

// ─── Tier helpers ─────────────────────────────────────────────────────────────

// Initial per-pick tier: marks BotD candidates; promotion to exactly one happens later.
function rawTier(edge: number | null, winProb: number): SubPickTier | null {
  const meetsEdge = edge === null || edge >= EDGE_MIN;
  if (!meetsEdge || winProb < PROB_MIN) return null;
  // BotD candidate — safe-zone (null edge) is never eligible
  if (edge !== null && edge >= BOTD_EDGE && winProb >= BOTD_PROB) return "Bet of the Day";
  return "Strong";
}

/**
 * Across all visible picks, find the single best BotD by edge × winProb.
 * Picks whose game is postponed/suspended/cancelled are excluded from BotD/Elite candidacy.
 * All other BotD candidates are demoted to "Elite".
 * Returns the promoted list and the winning key (null if no candidates).
 */
function promoteTiers(
  picks: SubPick[],
  postponedGameIds?: Set<string>,
): { picks: SubPick[]; botdKey: string | null } {
  const candidates = picks.filter(
    (p) => p.tier === "Bet of the Day" && !postponedGameIds?.has(p.gameId),
  );
  if (candidates.length === 0) return { picks, botdKey: null };

  // Sort candidates: score DESC, then edge DESC, then winProb DESC
  const sorted = [...candidates].sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    if ((b.edge ?? 0) !== (a.edge ?? 0)) return (b.edge ?? 0) - (a.edge ?? 0);
    return b.winProb - a.winProb;
  });

  const botdKey = sorted[0].key;

  return {
    botdKey,
    picks: picks.map((p) =>
      p.tier === "Bet of the Day" && p.key !== botdKey
        ? { ...p, tier: "Elite" as SubPickTier }
        : p
    ),
  };
}

// ─── Per-source filter functions ──────────────────────────────────────────────

function filterSharpPicks(picks: MLBSharpPick[]): SubPick[] {
  return picks.flatMap((p): SubPick[] => {
    if (!p.isRealValue) return [];
    const edge = p.edge ?? 0;
    const winProb = p.calibratedConfidence ?? 0;
    const tier = rawTier(edge, winProb);
    if (!tier) return [];
    return [{
      key: `sharp-${p.gameId}-${p.market}`,
      gameId: p.gameId,
      gameTime: p.gameTime,
      homeTeam: p.homeTeam,
      awayTeam: p.awayTeam,
      source: "sharp",
      label: p.pick,
      marketLabel: GAME_MARKET_LABELS[p.market] ?? p.market,
      edge,
      winProb,
      score: edge * winProb,
      oddsDecimal: p.oddsDecimal,
      oddsAmerican: p.oddsAmerican,
      tier,
    }];
  });
}

function filterSafeZone(picks: MLBSafeZonePick[]): SubPick[] {
  return picks.flatMap((p): SubPick[] => {
    const result: SubPick[] = [];

    const bankProb = p.bankerProb ?? 0;
    if (p.bankerPick && bankProb >= PROB_MIN) {
      const tier = rawTier(null, bankProb);
      if (tier) result.push({
        key: `banker-${p.gameId}`,
        gameId: p.gameId,
        gameTime: p.gameTime,
        homeTeam: p.homeTeam,
        awayTeam: p.awayTeam,
        source: "banker",
        label: p.bankerPick,
        marketLabel: "Safe Banker",
        edge: null,
        winProb: bankProb,
        score: 0, // safe-zone picks cannot be BotD; score used only for group sort
        oddsDecimal: null,
        oddsAmerican: null,
        tier,
      });
    }

    const balProb = p.balancedProb ?? 0;
    if (p.balancedPick && balProb >= PROB_MIN) {
      const tier = rawTier(null, balProb);
      if (tier) result.push({
        key: `balanced-${p.gameId}`,
        gameId: p.gameId,
        gameTime: p.gameTime,
        homeTeam: p.homeTeam,
        awayTeam: p.awayTeam,
        source: "balanced",
        label: p.balancedPick,
        marketLabel: "Safe Balanced",
        edge: null,
        winProb: balProb,
        score: 0,
        oddsDecimal: null,
        oddsAmerican: null,
        tier,
      });
    }

    return result;
  });
}

function filterProps(props: MLBPlayerProp[]): SubPick[] {
  return props.flatMap((p): SubPick[] => {
    if (p.edgeFlag === "suspect" || p.edgeFlag === "no-odds") return [];
    const edge = p.modelEdge ?? 0;
    if (edge < EDGE_MIN) return [];
    const rawProb = p.calibratedOverProb ?? 50;
    const winProb = p.pickSide === "Under" ? 100 - rawProb : rawProb;
    const tier = rawTier(edge, winProb);
    if (!tier) return [];
    const mktLabel = PROP_LABELS[p.propMarket] ?? p.propMarket;
    return [{
      key: `prop-${p.gameId}-${p.playerName}-${p.propMarket}`,
      gameId: p.gameId,
      gameTime: p.gameTime,
      homeTeam: p.homeTeam,
      awayTeam: p.awayTeam,
      source: "prop",
      label: `${p.pickSide} ${p.marketLine} ${mktLabel}`,
      marketLabel: mktLabel,
      edge,
      winProb,
      score: edge * winProb,
      oddsDecimal: p.bestOddsDecimal,
      oddsAmerican: p.bestOddsAmerican,
      tier,
      playerName: p.playerName,
    }];
  });
}

// ─── Game grouping (with prop cap) ───────────────────────────────────────────
type GameGroup = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  gameTime: string | null;
  picks: SubPick[];
};

function gameDateToronto(gameTime: string | null): string | null {
  if (!gameTime) return null;
  const d = new Date(gameTime);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto" }).format(d);
}

const TIER_ORDER: Record<SubPickTier, number> = { "Bet of the Day": 0, "Elite": 1, "Strong": 2 };

function pickSorter(a: SubPick, b: SubPick): number {
  const to = TIER_ORDER[a.tier] - TIER_ORDER[b.tier];
  if (to !== 0) return to;
  if (b.score !== a.score) return b.score - a.score;
  if ((b.edge ?? 0) !== (a.edge ?? 0)) return (b.edge ?? 0) - (a.edge ?? 0);
  return b.winProb - a.winProb;
}

function buildGroups(picks: SubPick[]): GameGroup[] {
  const map = new Map<string, GameGroup>();
  for (const p of picks) {
    if (!map.has(p.gameId)) {
      map.set(p.gameId, {
        gameId: p.gameId,
        homeTeam: p.homeTeam,
        awayTeam: p.awayTeam,
        gameTime: p.gameTime,
        picks: [],
      });
    }
    map.get(p.gameId)!.picks.push(p);
  }

  for (const g of map.values()) {
    const nonProps = g.picks.filter((p) => p.source !== "prop");
    // Cap props at MAX_PROPS_PER_GAME, ranked by score then edge then prob
    const props = g.picks
      .filter((p) => p.source === "prop")
      .sort(pickSorter)
      .slice(0, MAX_PROPS_PER_GAME);
    g.picks = [...nonProps, ...props].sort(pickSorter);
  }

  return [...map.values()].sort((a, b) =>
    (a.gameTime ?? "").localeCompare(b.gameTime ?? "")
  );
}

// ─── Source badge styles ──────────────────────────────────────────────────────
const SOURCE_STYLE: Record<PickSource, string> = {
  sharp:    "border-accent-2/40 bg-accent-2/10 text-accent-2",
  balanced: "border-elite/40   bg-elite/10    text-elite",
  banker:   "border-watch/40   bg-watch/10    text-watch",
  prop:     "border-border-strong/60 bg-white/5 text-muted",
};

const SOURCE_LABEL: Record<PickSource, string> = {
  sharp:    "Sharp",
  balanced: "Balanced",
  banker:   "Banker",
  prop:     "Prop",
};

// ─── Odds formatter ───────────────────────────────────────────────────────────
function fmtOdds(american: number | null, decimal: number | null): string | null {
  if (american != null) return `${american > 0 ? "+" : ""}${american}`;
  if (decimal != null)  return `×${decimal.toFixed(2)}`;
  return null;
}

// ─── Bet of the Day featured card ─────────────────────────────────────────────
function BetOfTheDayCard({
  pick,
  liveState,
}: {
  pick: SubPick;
  liveState?: Map<string, LiveScore>;
}) {
  const live = liveState?.get(pick.gameId);
  const isLive = live?.isLive ?? false;
  const oddsStr = fmtOdds(pick.oddsAmerican, pick.oddsDecimal);

  return (
    <div className="rounded-2xl border-2 border-watch/55 bg-watch/8 p-5 shadow-lg shadow-watch/10">
      {/* Header */}
      <div className="mb-4 flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-watch/50 bg-watch/20 px-3 py-1 text-xs font-bold text-watch">
          ★ BET OF THE DAY
        </span>
        <span className="text-[10px] text-muted/50">single highest-conviction play</span>
      </div>

      {/* Matchup */}
      <div className="mb-1 flex items-center gap-1.5 flex-wrap">
        <TeamLogo team={pick.awayTeam} size={20} />
        <span className="text-sm font-semibold text-ink">{pick.awayTeam}</span>
        <span className="text-muted text-xs">@</span>
        <TeamLogo team={pick.homeTeam} size={20} />
        <span className="text-sm font-semibold text-ink">{pick.homeTeam}</span>
        {isLive && (
          <span className="ml-1 flex items-center gap-1">
            <span className="size-1.5 rounded-full bg-watch animate-pulse" />
            <span className="text-[10px] font-bold text-watch uppercase tracking-wide">Live</span>
          </span>
        )}
      </div>
      <p className="mb-4 text-xs text-muted">{formatFirstPitch(pick.gameTime)}</p>

      {/* The pick */}
      <div className="rounded-xl border border-watch/30 bg-bg-2/60 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-watch/70">
              {pick.marketLabel}
            </p>
            <p className="mt-0.5 text-xl font-bold text-ink">{pick.label}</p>
            {pick.playerName && (
              <p className="mt-0.5 text-xs text-muted">{pick.playerName}</p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-4 text-right">
            {pick.edge !== null && (
              <div>
                <p className="text-[10px] text-muted/50">Edge</p>
                <p className="text-sm font-bold text-elite">+{pick.edge.toFixed(1)}%</p>
              </div>
            )}
            <div>
              <p className="text-[10px] text-muted/50">Win%</p>
              <p className="text-sm font-bold text-watch">{pick.winProb.toFixed(1)}%</p>
            </div>
            {oddsStr && (
              <div>
                <p className="text-[10px] text-muted/50">Odds</p>
                <p className="text-sm font-mono text-muted">{oddsStr}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Live score */}
      {live && (
        <LiveScoreModule
          live={live}
          market={pick.source === "prop" ? "totals" : pick.marketLabel.toLowerCase()}
          pick={pick.label}
          homeTeam={pick.homeTeam}
          awayTeam={pick.awayTeam}
        />
      )}
    </div>
  );
}

// ─── Elite section ────────────────────────────────────────────────────────────

function ElitePickCard({
  pick,
  liveState,
}: {
  pick: SubPick;
  liveState?: Map<string, LiveScore>;
}) {
  const live = liveState?.get(pick.gameId);
  const isLive = live?.isLive ?? false;
  const oddsStr = fmtOdds(pick.oddsAmerican, pick.oddsDecimal);

  return (
    <div className="rounded-xl border border-violet-500/25 bg-bg-2/50 px-4 py-3">
      {/* Matchup row */}
      <div className="mb-2 flex items-center gap-1.5 flex-wrap">
        <TeamLogo team={pick.awayTeam} size={16} />
        <span className="text-xs font-semibold text-ink">{pick.awayTeam}</span>
        <span className="text-muted text-[10px]">@</span>
        <TeamLogo team={pick.homeTeam} size={16} />
        <span className="text-xs font-semibold text-ink">{pick.homeTeam}</span>
        {isLive && (
          <span className="ml-0.5 flex items-center gap-1">
            <span className="size-1.5 rounded-full bg-watch animate-pulse" />
            <span className="text-[10px] font-bold text-watch uppercase tracking-wide">Live</span>
          </span>
        )}
        <span className="ml-auto text-[10px] text-muted/60">{formatFirstPitch(pick.gameTime)}</span>
      </div>

      {/* Pick row */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-400/70">
            {pick.marketLabel}
          </p>
          <p className="mt-0.5 text-sm font-bold text-ink">{pick.label}</p>
          {pick.playerName && (
            <p className="mt-0.5 text-[10px] text-muted/55">{pick.playerName}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3 text-right">
          {pick.edge !== null && (
            <div>
              <p className="text-[10px] text-muted/50">Edge</p>
              <p className="text-xs font-bold text-elite">+{pick.edge.toFixed(1)}%</p>
            </div>
          )}
          <div>
            <p className="text-[10px] text-muted/50">Win%</p>
            <p className="text-xs font-bold text-violet-300">{pick.winProb.toFixed(1)}%</p>
          </div>
          {oddsStr && (
            <div>
              <p className="text-[10px] text-muted/50">Odds</p>
              <p className="text-xs font-mono text-muted">{oddsStr}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function EliteSection({
  picks,
  liveState,
}: {
  picks: SubPick[];
  liveState?: Map<string, LiveScore>;
}) {
  if (picks.length === 0) return null;

  return (
    <div className="rounded-2xl border border-violet-500/30 bg-violet-500/5 p-4">
      {/* Header — retains the existing Elite count label */}
      <div className="mb-3 flex items-center gap-2">
        <span className="inline-flex items-center rounded-full border border-violet-400/50 bg-violet-500/15 px-3 py-1 text-xs font-bold text-violet-300">
          {picks.length} Elite play{picks.length !== 1 ? "s" : ""}
        </span>
        <span className="text-[10px] text-muted/50">meets BotD bar, not today&apos;s top pick</span>
      </div>

      <div className="flex flex-col gap-2">
        {picks.map((pick) => (
          <ElitePickCard key={pick.key} pick={pick} liveState={liveState} />
        ))}
      </div>
    </div>
  );
}

// ─── Pick row ─────────────────────────────────────────────────────────────────
function PickRow({ pick }: { pick: SubPick }) {
  const isBotD  = pick.tier === "Bet of the Day";
  const isElite = pick.tier === "Elite";
  const oddsStr = fmtOdds(pick.oddsAmerican, pick.oddsDecimal);

  return (
    <div
      className={`flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl px-3 py-2.5 ${
        isBotD  ? "bg-watch/5 ring-1 ring-watch/25"
        : isElite ? "bg-violet-500/5 ring-1 ring-violet-500/20"
        : "bg-white/[0.02] ring-1 ring-border/30"
      }`}
    >
      {/* Tier badge */}
      {isBotD ? (
        <span className="shrink-0 inline-flex items-center gap-1 rounded-full border border-watch/50 bg-watch/20 px-2 py-0.5 text-[10px] font-bold tracking-wide text-watch">
          ★ BET OF THE DAY
        </span>
      ) : isElite ? (
        <span className="shrink-0 inline-flex items-center rounded-full border border-violet-400/50 bg-violet-500/15 px-2 py-0.5 text-[10px] font-bold text-violet-300">
          Elite
        </span>
      ) : (
        <span className="shrink-0 inline-flex items-center rounded-full border border-elite/40 bg-elite/10 px-2 py-0.5 text-[10px] font-semibold text-elite">
          Strong
        </span>
      )}

      {/* Source badge */}
      <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${SOURCE_STYLE[pick.source]}`}>
        {SOURCE_LABEL[pick.source]}
      </span>

      {/* Pick label */}
      <div className="flex min-w-0 flex-1 flex-col gap-px">
        {pick.playerName && (
          <span className="text-[10px] leading-none text-muted/55">{pick.playerName}</span>
        )}
        <span className="truncate text-xs font-semibold text-ink">{pick.label}</span>
        <span className="text-[10px] leading-none text-muted/40">{pick.marketLabel}</span>
      </div>

      {/* Stats */}
      <div className="ml-auto flex shrink-0 items-center gap-4 text-right">
        {pick.edge !== null && (
          <div>
            <p className="text-[10px] text-muted/50">Edge</p>
            <p className="text-xs font-bold text-elite">+{pick.edge.toFixed(1)}%</p>
          </div>
        )}
        <div>
          <p className="text-[10px] text-muted/50">Win%</p>
          <p className={`text-xs font-bold ${isBotD ? "text-watch" : isElite ? "text-violet-300" : "text-ink"}`}>
            {pick.winProb.toFixed(1)}%
          </p>
        </div>
        {oddsStr && (
          <div>
            <p className="text-[10px] text-muted/50">Odds</p>
            <p className="text-xs font-mono text-muted">{oddsStr}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Game card ────────────────────────────────────────────────────────────────
function GameCard({
  group,
  liveState,
  lineupConfirmed,
  postponedGameIds,
}: {
  group: GameGroup;
  liveState?: Map<string, LiveScore>;
  lineupConfirmed: boolean;
  postponedGameIds?: Set<string>;
}) {
  const isPostponed = postponedGameIds?.has(group.gameId) ?? false;
  const hasBotD  = !isPostponed && group.picks.some((p) => p.tier === "Bet of the Day");
  const hasElite = !isPostponed && !hasBotD && group.picks.some((p) => p.tier === "Elite");
  const live    = liveState?.get(group.gameId);
  const isLive  = live?.isLive ?? false;

  // Split picks: non-props always visible; props in collapsible section
  const nonPropPicks = group.picks.filter((p) => p.source !== "prop");
  const propPicks    = group.picks.filter((p) => p.source === "prop");
  const hasPropPicks = propPicks.length > 0;

  // Auto-expand when lineup is confirmed AND there are qualifying props to show
  const [propsOpen, setPropsOpen] = useState(lineupConfirmed && hasPropPicks);

  const topPick = nonPropPicks[0] ?? propPicks[0];

  const borderClass = isPostponed
    ? "border-red-500/20 opacity-70"
    : hasBotD
    ? "border-watch/35"
    : hasElite
    ? "border-violet-400/30"
    : "border-border";

  return (
    <div className={`rounded-2xl border bg-surface p-4 backdrop-blur ${borderClass}`}>
      {/* Game header */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <TeamLogo team={group.awayTeam} size={18} />
            <span className="text-sm font-semibold text-ink">{group.awayTeam}</span>
            <span className="text-muted text-xs">@</span>
            <TeamLogo team={group.homeTeam} size={18} />
            <span className="text-sm font-semibold text-ink">{group.homeTeam}</span>
          </div>
          <div className="mt-0.5 flex items-center gap-2 flex-wrap">
            <p className="text-xs text-muted">{formatFirstPitch(group.gameTime)}</p>
            {isPostponed && (
              <span className="inline-flex items-center rounded border border-red-400/40 bg-red-400/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-red-400">
                Postponed
              </span>
            )}
            {!isPostponed && isLive && (
              <span className="flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-watch animate-pulse" />
                <span className="text-[10px] font-bold text-watch uppercase tracking-wide">Live</span>
              </span>
            )}
            {/* Lineup status badge */}
            {lineupConfirmed ? (
              <span className="flex items-center gap-0.5 text-[10px] font-semibold text-elite">
                <span>✓</span>
                <span>Lineup confirmed</span>
              </span>
            ) : hasPropPicks ? (
              <span className="text-[10px] text-muted/45">Lineup pending</span>
            ) : null}
          </div>
        </div>
        <span className="shrink-0 rounded-full border border-border-strong/40 bg-bg-2 px-2.5 py-0.5 text-[10px] text-muted">
          {group.picks.length} play{group.picks.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Non-prop picks (always visible) */}
      {nonPropPicks.length > 0 && (
        <div className="flex flex-col gap-2">
          {nonPropPicks.map((pick) => (
            <PickRow key={pick.key} pick={pick} />
          ))}
        </div>
      )}

      {/* Props collapsible section */}
      {hasPropPicks && (
        <div className={nonPropPicks.length > 0 ? "mt-2" : ""}>
          <button
            onClick={() => setPropsOpen((o) => !o)}
            className="flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-left text-[11px] text-muted transition-colors hover:bg-white/5"
          >
            <span className="flex items-center gap-1.5">
              <span>⚾ Player Props</span>
              <span className="rounded-full border border-border-strong/40 bg-bg-2 px-1.5 py-0.5 text-[10px]">
                {propPicks.length}
              </span>
              {lineupConfirmed ? (
                <span className="text-[10px] font-semibold text-elite">✓ Lineup confirmed</span>
              ) : (
                <span className="text-[10px] text-muted/45">Lineup pending</span>
              )}
            </span>
            <span className="shrink-0 text-muted/50">{propsOpen ? "▲" : "▼"}</span>
          </button>

          {propsOpen && (
            <div className="mt-1.5 flex flex-col gap-2">
              {propPicks.map((pick) => (
                <PickRow key={pick.key} pick={pick} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Live score */}
      {live && topPick && (
        <LiveScoreModule
          live={live}
          market={topPick.source === "prop" ? "totals" : topPick.marketLabel.toLowerCase()}
          pick={topPick.label}
          homeTeam={group.homeTeam}
          awayTeam={group.awayTeam}
        />
      )}
    </div>
  );
}

// ─── Subscriber track record ─────────────────────────────────────────────────

const MIN_SAMPLE = 30;

function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="text-[10px] text-muted/55">{label}</p>
      <p className="mt-0.5 text-sm font-bold text-ink">{value}</p>
    </div>
  );
}

function SegmentStats({ label, seg }: { label: string; seg: MLBSubscriberSegment | null }) {
  if (!seg || seg.pickCount === 0) {
    return (
      <div className="flex-1 rounded-xl border border-border/40 bg-bg-2/50 px-4 py-3 text-center">
        <p className="text-xs font-semibold text-muted">{label}</p>
        <p className="mt-1 text-[10px] text-muted/50">No graded picks yet</p>
      </div>
    );
  }
  const n   = seg.pickCount;
  const wl  = `${seg.winCount}-${seg.lossCount}`;
  const wr  = seg.winRate   != null ? `${(seg.winRate * 100).toFixed(1)}%` : "—";
  const roi = seg.roiPercent != null ? `${seg.roiPercent > 0 ? "+" : ""}${seg.roiPercent.toFixed(1)}%` : "—";
  const edge = seg.avgEdge   != null ? `+${seg.avgEdge.toFixed(1)}%` : "—";
  const prob = seg.avgWinProb != null ? `${seg.avgWinProb.toFixed(1)}%` : "—";
  const clv  = seg.avgClv    != null ? `${seg.avgClv > 0 ? "+" : ""}${seg.avgClv.toFixed(2)}%` : "(no data)";

  return (
    <div className="flex-1 rounded-xl border border-border/40 bg-bg-2/50 px-4 py-3">
      <p className="mb-2 text-center text-xs font-semibold text-ink">{label}</p>
      {n < MIN_SAMPLE && (
        <p className="mb-2 rounded border border-watch/30 bg-watch/5 px-2 py-1 text-center text-[10px] text-watch">
          INSUFFICIENT DATA (n={n} &lt; {MIN_SAMPLE}) — results not yet meaningful
        </p>
      )}
      <div className="grid grid-cols-3 gap-3">
        <StatCell label="Record (W-L)" value={wl} />
        <StatCell label="Win %" value={wr} />
        <StatCell label="ROI" value={roi} />
        <StatCell label="Avg Edge" value={edge} />
        <StatCell label="Avg Win%" value={prob} />
        <StatCell label="Avg CLV" value={clv} />
      </div>
    </div>
  );
}

function SubscriberTrackRecord({ gradedPicks }: { gradedPicks: MLBPickDetail[] }) {
  const [trDateFilter, setTrDateFilter] = useState("all");

  const qualifiedAll  = gradedPicks.filter(isQualified);
  const qualifiedBotD = gradedPicks.filter(isBotD);

  const trDates = [...new Set(
    qualifiedAll.map((p) => p.gameDate).filter(Boolean) as string[]
  )].sort().reverse();
  const last7Set = new Set(trDates.slice(0, 7));

  function applyTrFilter(rows: MLBPickDetail[]): MLBPickDetail[] {
    if (trDateFilter === "all") return rows;
    if (trDateFilter === "last7") return rows.filter((p) => last7Set.has(p.gameDate ?? ""));
    return rows.filter((p) => p.gameDate === trDateFilter);
  }

  const segAll  = computeSegment(applyTrFilter(qualifiedAll));
  const segBotD = computeSegment(applyTrFilter(qualifiedBotD));

  return (
    <div className="mt-2 rounded-2xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-bold text-ink">Subscriber Track Record</p>
        <span className="rounded-sm bg-watch/20 px-1.5 py-0.5 text-[9px] font-bold text-watch">
          INTERNAL
        </span>
      </div>

      <p className="mb-3 text-[10px] leading-relaxed text-muted/70">
        Performance of picks that qualified under the subscriber filter (edge ≥ +{EDGE_MIN}%,
        win prob ≥ {PROB_MIN}%) across all graded game picks and player props.{" "}
        <span className="font-semibold text-watch">CLV is the primary signal.</span>{" "}
        Win% and ROI are secondary — favourites bias applies.
      </p>

      <DateSelector dates={trDates} selected={trDateFilter} onChange={setTrDateFilter} showLast7 />

      <div className="flex flex-col gap-3 sm:flex-row">
        <SegmentStats label="All Qualifying Plays" seg={segAll} />
        <SegmentStats label="★ BotD-quality plays" seg={segBotD} />
      </div>
    </div>
  );
}

// ─── Main export ─────────────────────────────────────────────────────────────
export function MLBSubscriberView({
  sharpPicks,
  safeZone,
  playerProps,
  liveState,
  gradedPicks = [],
}: {
  sharpPicks: MLBSharpPick[];
  safeZone: MLBSafeZonePick[];
  playerProps: MLBPlayerProp[];
  liveState?: Map<string, LiveScore>;
  gradedPicks?: MLBPickDetail[];
}) {
  const [dateFilter, setDateFilter] = useState("all");

  // Lineup confirmation: a game's batting lineup is confirmed when it has batter props.
  // Pitcher-only props do not count — batter props require lineup submission.
  const lineupConfirmedGameIds = new Set(
    playerProps
      .filter((p) => p.playerType === "batter")
      .map((p) => p.gameId)
  );

  // Compute postponed game IDs from live state — mirrors the grader's POSTPONED_STATUSES set.
  const postponedGameIds = new Set<string>();
  if (liveState) {
    for (const [gameId, live] of liveState) {
      if (isPostponedStatus(live.gameStatus)) postponedGameIds.add(gameId);
    }
  }

  const rawPicks: SubPick[] = [
    ...filterSharpPicks(sharpPicks),
    ...filterSafeZone(safeZone),
    ...filterProps(playerProps),
  ];

  const dates = [...new Set(
    rawPicks.map((p) => gameDateToronto(p.gameTime)).filter(Boolean) as string[]
  )].sort();

  const filteredRaw =
    dateFilter === "all"
      ? rawPicks
      : rawPicks.filter((p) => gameDateToronto(p.gameTime) === dateFilter);

  // Promote exactly one BotD across the current date's visible picks,
  // skipping any picks whose game is postponed/suspended/cancelled.
  const { picks: visiblePicks, botdKey } = promoteTiers(filteredRaw, postponedGameIds);

  const botdPick  = botdKey ? visiblePicks.find((p) => p.key === botdKey) ?? null : null;
  // Elite section also excludes postponed games.
  const elitePicks = visiblePicks.filter(
    (p) => p.tier === "Elite" && !postponedGameIds.has(p.gameId),
  );

  const groups = buildGroups(visiblePicks);

  return (
    <div className="flex flex-col gap-5">
      {/* Honesty guardrail */}
      <div className="rounded-xl border border-watch/30 bg-watch/5 px-4 py-3 text-xs leading-relaxed text-muted">
        <span className="font-bold text-watch">INTERNAL — Do not share or bet real money.</span>{" "}
        This is a paper-trading view only. The Poisson model is unproven and still accumulating
        signal. All plays shown are for internal validation. Edge and probability figures are
        model outputs, not verified predictions.
      </div>

      {/* Qualifying criteria legend */}
      <div className="rounded-lg border border-border/40 bg-bg-2/50 px-4 py-2.5 text-xs text-muted/80">
        <span className="font-semibold text-ink">Qualifying criteria:</span>{" "}
        Edge ≥ +{EDGE_MIN}% (where applicable) · Win prob ≥ {PROB_MIN}% · No suspect / no-odds flags
        <span className="mx-2 text-border-strong">·</span>
        <span className="font-semibold text-watch">★ Bet of the Day</span>{" "}
        = single best play by edge × prob (edge ≥ +{BOTD_EDGE}% &amp; prob ≥ {BOTD_PROB}% required)
        <span className="mx-2 text-border-strong">·</span>
        <span className="font-semibold text-violet-300">Elite</span>{" "}
        = BotD-bar met but not selected · Props capped at {MAX_PROPS_PER_GAME} per game
      </div>

      {/* Date selector */}
      <DateSelector dates={dates} selected={dateFilter} onChange={setDateFilter} />

      {/* ★ Bet of the Day — dedicated featured section */}
      {botdPick && (
        <BetOfTheDayCard pick={botdPick} liveState={liveState} />
      )}

      {/* Elite section — grouped featured section, below BotD, above game list */}
      <EliteSection picks={elitePicks} liveState={liveState} />

      {/* Game list */}
      {groups.length === 0 ? (
        <EmptyState
          title="No qualifying plays"
          subtitle={
            dateFilter !== "all"
              ? "No plays clear the filter on the selected date. Try 'All dates' or check back as odds firm up."
              : `No picks currently clear edge ≥ +${EDGE_MIN}% with win prob ≥ ${PROB_MIN}%. Check back closer to first pitch.`
          }
        />
      ) : (
        <div className="flex flex-col gap-4">
          {groups.map((g) => (
            <GameCard
              key={g.gameId}
              group={g}
              liveState={liveState}
              lineupConfirmed={lineupConfirmedGameIds.has(g.gameId)}
              postponedGameIds={postponedGameIds}
            />
          ))}
        </div>
      )}

      {groups.length > 0 && (
        <p className="text-right text-[10px] text-muted/40">
          {visiblePicks.length} qualifying play{visiblePicks.length !== 1 ? "s" : ""} across{" "}
          {groups.length} game{groups.length !== 1 ? "s" : ""}
          {" · "}{MAX_PROPS_PER_GAME} props/game max
        </p>
      )}

      {/* Track record */}
      <SubscriberTrackRecord gradedPicks={gradedPicks} />
    </div>
  );
}
