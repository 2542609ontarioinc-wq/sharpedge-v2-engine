"use client";

import { useState } from "react";
import type { MLBPlayerProp, MLBSafeZonePick, MLBSharpPick } from "@/lib/types";
import { DateSelector } from "./DateSelector";
import { formatFirstPitch } from "@/lib/format";
import { EmptyState } from "./EmptyState";

// ─── Filter thresholds ──────────────────────────────────────────────────────
const EDGE_MIN  = 3;   // min model edge % for picks that carry an edge signal
const PROB_MIN  = 65;  // min win-probability % for all pick types
const BOTD_EDGE = 5;   // Bet of the Day: edge >= this
const BOTD_PROB = 70;  // Bet of the Day: win prob >= this

// ─── Unified pick shape ─────────────────────────────────────────────────────
type PickSource = "sharp" | "balanced" | "banker" | "prop";

type SubPick = {
  key: string;
  gameId: string;
  gameTime: string | null;
  homeTeam: string;
  awayTeam: string;
  source: PickSource;
  label: string;       // "Cardinals ML", "Over 5.5 Strikeouts", …
  marketLabel: string; // e.g. "Moneyline", "Strikeouts", "Safe Banker"
  edge: number | null; // null for safe-zone picks (no model edge available)
  winProb: number;     // probability of the chosen side, 0–100
  oddsDecimal: number | null;
  oddsAmerican: number | null;
  tier: "Bet of the Day" | "Strong";
  playerName?: string;
};

// ─── Market display labels ──────────────────────────────────────────────────
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

// ─── Tier assignment ────────────────────────────────────────────────────────
function calcTier(edge: number | null, winProb: number): "Bet of the Day" | "Strong" | null {
  if (edge !== null && edge >= BOTD_EDGE && winProb >= BOTD_PROB) return "Bet of the Day";
  const meetsEdge = edge === null || edge >= EDGE_MIN;
  if (meetsEdge && winProb >= PROB_MIN) return "Strong";
  return null;
}

// ─── Per-market filter functions ────────────────────────────────────────────

function filterSharpPicks(picks: MLBSharpPick[]): SubPick[] {
  return picks.flatMap((p): SubPick[] => {
    // isRealValue already gates: edge_flag === "REAL" && edge > 0 && edge ≤ 15
    if (!p.isRealValue) return [];
    const edge = p.edge ?? 0;
    const winProb = p.calibratedConfidence ?? 0;
    const tier = calcTier(edge, winProb);
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
      oddsDecimal: p.oddsDecimal,
      oddsAmerican: p.oddsAmerican,
      tier,
    }];
  });
}

function filterSafeZone(picks: MLBSafeZonePick[]): SubPick[] {
  // Safe-zone picks carry no model edge — only the probability filter applies.
  // Banker (higher-confidence) before balanced within each game.
  return picks.flatMap((p): SubPick[] => {
    const result: SubPick[] = [];

    const bankProb = p.bankerProb ?? 0;
    if (p.bankerPick && bankProb >= PROB_MIN) {
      const tier = calcTier(null, bankProb);
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
        oddsDecimal: null,
        oddsAmerican: null,
        tier,
      });
    }

    const balProb = p.balancedProb ?? 0;
    if (p.balancedPick && balProb >= PROB_MIN) {
      const tier = calcTier(null, balProb);
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
    // Win prob = probability of the chosen side (calibratedOverProb is always the Over prob)
    const rawProb = p.calibratedOverProb ?? 50;
    const winProb = p.pickSide === "Under" ? 100 - rawProb : rawProb;
    const tier = calcTier(edge, winProb);
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
      oddsDecimal: p.bestOddsDecimal,
      oddsAmerican: p.bestOddsAmerican,
      tier,
      playerName: p.playerName,
    }];
  });
}

// ─── Game grouping ──────────────────────────────────────────────────────────
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
  // Within each game: BotD first, then by edge desc, then by winProb desc
  for (const g of map.values()) {
    g.picks.sort((a, b) => {
      if (a.tier === "Bet of the Day" && b.tier !== "Bet of the Day") return -1;
      if (b.tier === "Bet of the Day" && a.tier !== "Bet of the Day") return 1;
      if ((b.edge ?? 0) !== (a.edge ?? 0)) return (b.edge ?? 0) - (a.edge ?? 0);
      return b.winProb - a.winProb;
    });
  }
  // Sort games by start time
  return [...map.values()].sort((a, b) =>
    (a.gameTime ?? "").localeCompare(b.gameTime ?? "")
  );
}

// ─── Source badge styles ────────────────────────────────────────────────────
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

// ─── Pick row ───────────────────────────────────────────────────────────────
function PickRow({ pick }: { pick: SubPick }) {
  const isBotD = pick.tier === "Bet of the Day";
  const amOdds = pick.oddsAmerican;
  const oddsStr =
    amOdds != null
      ? `${amOdds > 0 ? "+" : ""}${amOdds}`
      : pick.oddsDecimal != null
      ? `×${pick.oddsDecimal.toFixed(2)}`
      : null;

  return (
    <div
      className={`flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl px-3 py-2.5 ${
        isBotD
          ? "bg-watch/5 ring-1 ring-watch/25"
          : "bg-white/[0.02] ring-1 ring-border/30"
      }`}
    >
      {/* Tier badge */}
      {isBotD ? (
        <span className="shrink-0 inline-flex items-center gap-1 rounded-full border border-watch/50 bg-watch/20 px-2 py-0.5 text-[10px] font-bold tracking-wide text-watch">
          ★ BET OF THE DAY
        </span>
      ) : (
        <span className="shrink-0 inline-flex items-center rounded-full border border-elite/40 bg-elite/10 px-2 py-0.5 text-[10px] font-semibold text-elite">
          Strong
        </span>
      )}

      {/* Source badge */}
      <span
        className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-semibold ${SOURCE_STYLE[pick.source]}`}
      >
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
          <p className={`text-xs font-bold ${isBotD ? "text-watch" : "text-ink"}`}>
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

// ─── Game card ──────────────────────────────────────────────────────────────
function GameCard({ group }: { group: GameGroup }) {
  const hasBotD = group.picks.some((p) => p.tier === "Bet of the Day");
  return (
    <div
      className={`rounded-2xl border bg-surface p-4 backdrop-blur ${
        hasBotD ? "border-watch/35" : "border-border"
      }`}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink">
            {group.awayTeam} <span className="text-muted">@</span> {group.homeTeam}
          </p>
          <p className="mt-0.5 text-xs text-muted">{formatFirstPitch(group.gameTime)}</p>
        </div>
        <span className="shrink-0 rounded-full border border-border-strong/40 bg-bg-2 px-2.5 py-0.5 text-[10px] text-muted">
          {group.picks.length} play{group.picks.length !== 1 ? "s" : ""}
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {group.picks.map((pick) => (
          <PickRow key={pick.key} pick={pick} />
        ))}
      </div>
    </div>
  );
}

// ─── Main export ────────────────────────────────────────────────────────────
export function MLBSubscriberView({
  sharpPicks,
  safeZone,
  playerProps,
}: {
  sharpPicks: MLBSharpPick[];
  safeZone: MLBSafeZonePick[];
  playerProps: MLBPlayerProp[];
}) {
  const [dateFilter, setDateFilter] = useState("all");

  const allPicks: SubPick[] = [
    ...filterSharpPicks(sharpPicks),
    ...filterSafeZone(safeZone),
    ...filterProps(playerProps),
  ];

  const dates = [...new Set(
    allPicks.map((p) => gameDateToronto(p.gameTime)).filter(Boolean) as string[]
  )].sort();

  const visiblePicks =
    dateFilter === "all"
      ? allPicks
      : allPicks.filter((p) => gameDateToronto(p.gameTime) === dateFilter);

  const groups = buildGroups(visiblePicks);
  const botdCount = visiblePicks.filter((p) => p.tier === "Bet of the Day").length;

  return (
    <div className="flex flex-col gap-5">
      {/* Honesty guardrail — always visible; review before making tab public */}
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
        = edge ≥ +{BOTD_EDGE}% &amp; prob ≥ {BOTD_PROB}%
      </div>

      {/* Date selector */}
      <DateSelector dates={dates} selected={dateFilter} onChange={setDateFilter} />

      {/* Bet of the Day summary pill */}
      {botdCount > 0 && (
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-watch/50 bg-watch/15 px-3 py-1 text-xs font-bold text-watch">
            ★ {botdCount} Bet{botdCount !== 1 ? "s" : ""} of the Day
          </span>
          <span className="text-xs text-muted/50">highest-conviction plays this slate</span>
        </div>
      )}

      {/* Game groups */}
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
            <GameCard key={g.gameId} group={g} />
          ))}
        </div>
      )}

      {groups.length > 0 && (
        <p className="text-right text-[10px] text-muted/40">
          {visiblePicks.length} qualifying play{visiblePicks.length !== 1 ? "s" : ""} across{" "}
          {groups.length} game{groups.length !== 1 ? "s" : ""}
        </p>
      )}
    </div>
  );
}
