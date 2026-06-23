"use client";

import { useState } from "react";
import type { MLBPickDetail, MLBPlayerProp, MLBSafeZonePick, MLBSharpPick, MLBSubscriberSegment } from "@/lib/types";
import { DateSelector } from "./DateSelector";
import { formatFirstPitch } from "@/lib/format";
import { EmptyState } from "./EmptyState";
import { TeamLogo } from "./TeamLogo";
import { LiveScoreModule } from "./LiveScoreModule";
import type { LiveScore } from "@/hooks/useLiveScores";

// ─── Filter thresholds ────────────────────────────────────────────────────────
const EDGE_MIN  = 3;
const PROB_MIN  = 65;
const BOTD_EDGE = 5;
const BOTD_PROB = 70;
const MAX_PROPS_PER_GAME = 2;
const MIN_SAMPLE = 30;     // building-field gate: N graded picks before showing real stats
const MIN_CLV_SAMPLE = 10; // CLV display gate: hide noisy avg below this sample count

// ─── Power Score ──────────────────────────────────────────────────────────────
// Weights: edge dominant (×3.0), prob above 50% secondary (×0.4).
// CLV and historical ROI excluded until sufficient graded data exists.
const PS_EDGE_W = 3.0;
const PS_PROB_W = 0.4;
function calcPowerScore(edge: number, winProb: number): number {
  return edge * PS_EDGE_W + Math.max(0, winProb - 50) * PS_PROB_W;
}

// ─── Book implied probability ─────────────────────────────────────────────────
function bookImplied(decimal: number | null, american: number | null): number | null {
  if (decimal !== null && decimal > 1) return (1 / decimal) * 100;
  if (american !== null) {
    if (american > 0) return (100 / (american + 100)) * 100;
    if (american < 0) return (Math.abs(american) / (Math.abs(american) + 100)) * 100;
  }
  return null;
}

// ─── Edge grade labels ─────────────────────────────────────────────────────────
type EdgeGrade = "Lean" | "Play" | "Strong" | "Elite";
function edgeGradeLabel(edge: number | null): EdgeGrade | null {
  if (edge === null) return null;
  if (edge >= 10) return "Elite";
  if (edge >= 8)  return "Strong";
  if (edge >= 5)  return "Play";
  if (edge >= 3)  return "Lean";
  return null;
}

const GRADE_CHIP: Record<EdgeGrade, string> = {
  Lean:   "border-blue-400/50 bg-blue-900/40 text-blue-300",
  Play:   "border-[#caa024]/60 bg-[#caa024]/15 text-[#f3c64a]",
  Strong: "border-cyan-400/50 bg-cyan-900/40 text-cyan-300",
  Elite:  "border-[#f3c64a]/70 bg-[#f3c64a]/20 text-[#f3c64a] font-extrabold tracking-widest",
};

// ─── Postponed detection ──────────────────────────────────────────────────────
// Mirrors POSTPONED_STATUSES in grade_mlb_picks.py / grade_mlb_prop_picks.py.
const POSTPONED_STATUS_SET = new Set(["postponed", "cancelled", "canceled", "suspended", "post"]);
function isPostponedStatus(gameStatus: string): boolean {
  const lower = gameStatus.toLowerCase().trim();
  if (POSTPONED_STATUS_SET.has(lower)) return true;
  const firstWord = lower.split(/[\s:]/)[0];
  return POSTPONED_STATUS_SET.has(firstWord);
}

// ─── Market panel config — blue=Totals, red=ML, amber=Props, green=Safe ──────
type MarketStyle = { border: string; bg: string; textColor: string; icon: string };
const MARKET_STYLE: Record<string, MarketStyle> = {
  moneyline:     { border: "border-red-500/50",    bg: "bg-red-950/60",    textColor: "text-red-400",    icon: "💰" },
  totals:        { border: "border-blue-400/50",   bg: "bg-blue-950/60",   textColor: "text-blue-400",   icon: "⬛" },
  run_line:      { border: "border-orange-400/50", bg: "bg-orange-950/60", textColor: "text-orange-400", icon: "📊" },
  safe_balanced: { border: "border-green-400/50",  bg: "bg-green-950/60",  textColor: "text-green-400",  icon: "✓" },
  safe_banker:   { border: "border-green-400/50",  bg: "bg-green-950/60",  textColor: "text-green-400",  icon: "✓" },
  prop:          { border: "border-amber-400/50",  bg: "bg-amber-950/60",  textColor: "text-amber-400",  icon: "⚾" },
};
function mktStyle(market: string): MarketStyle {
  return MARKET_STYLE[market] ?? { border: "border-[#caa024]/25", bg: "bg-[#070a10]", textColor: "text-[#f3c64a]", icon: "📌" };
}

// ─── Segment computation (unchanged) ─────────────────────────────────────────
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
    clvSampleCount: clvRows.length,
  };
}

// ─── Market graded stats — for "Building (N/30)" field gating ─────────────────
type MarketGradedStats = {
  n: number;           // qualifying graded picks in this market
  winRate: number | null;  // real value once n >= MIN_SAMPLE
  roi: number | null;      // real value once n >= MIN_SAMPLE
};

function computeMarketGradedStats(gradedPicks: MLBPickDetail[]): Map<string, MarketGradedStats> {
  const acc = new Map<string, { wins: number; n: number; roiSum: number }>();
  for (const p of gradedPicks) {
    if (!isQualified(p)) continue;
    if (p.grade !== "WIN" && p.grade !== "LOSS") continue;
    const s = acc.get(p.market) ?? { wins: 0, n: 0, roiSum: 0 };
    s.n++;
    if (p.grade === "WIN") s.wins++;
    s.roiSum += p.roiPercent ?? 0;
    acc.set(p.market, s);
  }
  const result = new Map<string, MarketGradedStats>();
  for (const [market, { wins, n, roiSum }] of acc) {
    result.set(market, {
      n,
      winRate: n >= MIN_SAMPLE ? (wins / n) * 100 : null,
      roi: n >= MIN_SAMPLE ? roiSum / n : null,
    });
  }
  return result;
}

// Returns the real value once n >= MIN_SAMPLE, otherwise "Building (n/MIN_SAMPLE)".
function buildingValue(n: number, realValue: string | null): string {
  if (realValue !== null && n >= MIN_SAMPLE) return realValue;
  return `Building (${n}/${MIN_SAMPLE})`;
}

// ─── SubPick type ─────────────────────────────────────────────────────────────
type PickSource = "sharp" | "balanced" | "banker" | "prop";
type SubPickTier = "Bet of the Day" | "Elite" | "Strong";

type SubPick = {
  key: string;
  gameId: string;
  gameTime: string | null;
  homeTeam: string;
  awayTeam: string;
  source: PickSource;
  market: string;
  label: string;
  marketLabel: string;
  edge: number | null;
  winProb: number;
  powerScore: number;
  bookImpliedProb: number | null;
  oddsDecimal: number | null;
  oddsAmerican: number | null;
  tier: SubPickTier;
  playerName?: string;
};

// ─── Market / source labels ───────────────────────────────────────────────────
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
function rawTier(edge: number | null, winProb: number): SubPickTier | null {
  const meetsEdge = edge === null || edge >= EDGE_MIN;
  if (!meetsEdge || winProb < PROB_MIN) return null;
  if (edge !== null && edge >= BOTD_EDGE && winProb >= BOTD_PROB) return "Bet of the Day";
  return "Strong";
}

/**
 * Promote exactly one BotD from picks, skipping postponed games.
 * Demotes all other BotD-tier picks to Elite.
 */
function promoteTiers(
  picks: SubPick[],
  postponedGameIds?: Set<string>,
): { picks: SubPick[]; botdKey: string | null } {
  const candidates = picks.filter(
    (p) => p.tier === "Bet of the Day" && !postponedGameIds?.has(p.gameId),
  );
  if (candidates.length === 0) {
    return {
      botdKey: null,
      picks: picks.map((p) =>
        p.tier === "Bet of the Day" ? { ...p, tier: "Elite" as SubPickTier } : p,
      ),
    };
  }

  const sorted = [...candidates].sort((a, b) => {
    if (b.powerScore !== a.powerScore) return b.powerScore - a.powerScore;
    if ((b.edge ?? 0) !== (a.edge ?? 0)) return (b.edge ?? 0) - (a.edge ?? 0);
    return b.winProb - a.winProb;
  });

  const botdKey = sorted[0].key;
  return {
    botdKey,
    picks: picks.map((p) =>
      p.tier === "Bet of the Day" && p.key !== botdKey
        ? { ...p, tier: "Elite" as SubPickTier }
        : p,
    ),
  };
}

// ─── Filter functions ─────────────────────────────────────────────────────────
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
      market: p.market,
      label: p.pick,
      marketLabel: GAME_MARKET_LABELS[p.market] ?? p.market,
      edge,
      winProb,
      powerScore: calcPowerScore(edge, winProb),
      bookImpliedProb: bookImplied(p.oddsDecimal, p.oddsAmerican),
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
        market: "safe_banker",
        label: p.bankerPick,
        marketLabel: "Safe Banker",
        edge: null,
        winProb: bankProb,
        powerScore: 0,
        bookImpliedProb: null,
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
        market: "safe_balanced",
        label: p.balancedPick,
        marketLabel: "Safe Balanced",
        edge: null,
        winProb: balProb,
        powerScore: 0,
        bookImpliedProb: null,
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
      market: "prop",
      label: `${p.pickSide} ${p.marketLine} ${mktLabel}`,
      marketLabel: mktLabel,
      edge,
      winProb,
      powerScore: calcPowerScore(edge, winProb),
      bookImpliedProb: bookImplied(p.bestOddsDecimal, p.bestOddsAmerican),
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
  if (b.powerScore !== a.powerScore) return b.powerScore - a.powerScore;
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

// ─── Odds formatter ───────────────────────────────────────────────────────────
function fmtOdds(american: number | null, decimal: number | null): string | null {
  if (american != null) return `${american > 0 ? "+" : ""}${american}`;
  if (decimal != null)  return `×${decimal.toFixed(2)}`;
  return null;
}

// ─── "Why we like it" rationale (real factors only, no placeholders) ──────────
function buildRationale(pick: SubPick): string {
  if (pick.edge === null) {
    return `Model assigns ${pick.winProb.toFixed(1)}% win probability — high-confidence safe zone.`;
  }
  const grade = edgeGradeLabel(pick.edge);
  const parts: string[] = [];
  if (grade) parts.push(`${grade}-grade edge: +${pick.edge.toFixed(1)}% above market price`);
  if (pick.bookImpliedProb !== null && pick.winProb - pick.bookImpliedProb > 0.5) {
    parts.push(`model at ${pick.winProb.toFixed(1)}% vs book implied ${pick.bookImpliedProb.toFixed(1)}%`);
  } else if (pick.bookImpliedProb === null) {
    parts.push(`model win probability ${pick.winProb.toFixed(1)}%`);
  }
  return parts.join(" · ");
}

// ─── GradeChip ────────────────────────────────────────────────────────────────
function GradeChip({ edge, large = false }: { edge: number | null; large?: boolean }) {
  const grade = edgeGradeLabel(edge);
  if (!grade) return null;
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 uppercase tracking-wide ${
      large ? "text-xs font-bold" : "text-[10px] font-bold"
    } ${GRADE_CHIP[grade]}`}>
      {grade}
    </span>
  );
}

// ─── PickFieldSet — all 9 fields per pick ─────────────────────────────────────
// REAL: Model Prob, Book Implied, Edge, Grade, Odds, CLV
// BUILDING: Hit Rate, Comparables, Expected ROI (shown honestly until n≥30)
function PickFieldSet({
  pick,
  marketStats,
  hero = false,
}: {
  pick: SubPick;
  marketStats: Map<string, MarketGradedStats>;
  hero?: boolean;
}) {
  const oddsStr = fmtOdds(pick.oddsAmerican, pick.oddsDecimal);
  const mStat = marketStats.get(pick.market);
  const gradedN = mStat?.n ?? 0;
  const hitRateStr = mStat?.winRate != null ? `${mStat.winRate.toFixed(1)}%` : null;
  const roiStr     = mStat?.roi     != null ? `${mStat.roi > 0 ? "+" : ""}${mStat.roi.toFixed(1)}%` : null;

  const MONO: React.CSSProperties = { fontFamily: "var(--font-mono-num, ui-monospace)" };
  const valClass = hero
    ? "text-2xl font-bold"
    : "text-sm font-semibold";
  const labelClass = "text-[10px] uppercase tracking-wide text-[#8ea5c5]/55";

  return (
    <div>
      {/* ── REAL fields ────────────────────────────────────────────────── */}
      <div className={`flex flex-wrap gap-x-5 gap-y-3 ${hero ? "mb-4" : "mb-2"}`}>
        {/* Model Probability */}
        <div>
          <p className={labelClass}>Model Prob</p>
          <p className={`${valClass} text-[#f3c64a]`} style={MONO}>
            {pick.winProb.toFixed(1)}%
          </p>
        </div>

        {/* Book Implied */}
        <div>
          <p className={labelClass}>Book Implied</p>
          {pick.bookImpliedProb !== null ? (
            <p className={`${valClass} text-[#8ea5c5]`} style={MONO}>
              {pick.bookImpliedProb.toFixed(1)}%
            </p>
          ) : (
            <p className={`${valClass} text-[#8ea5c5]/40`} style={MONO}>no-odds</p>
          )}
        </div>

        {/* Edge */}
        <div>
          <p className={labelClass}>Edge</p>
          {pick.edge !== null ? (
            <p className={`${valClass} text-[#12f38b]`} style={MONO}>
              +{pick.edge.toFixed(1)}%
            </p>
          ) : (
            <p className={`${valClass} text-[#8ea5c5]/40`} style={MONO}>—</p>
          )}
        </div>

        {/* Grade */}
        <div>
          <p className={labelClass}>Grade</p>
          <div className="mt-1">
            {edgeGradeLabel(pick.edge) ? (
              <GradeChip edge={pick.edge} large={hero} />
            ) : (
              <span className="text-[#8ea5c5]/40 text-xs">—</span>
            )}
          </div>
        </div>

        {/* Odds */}
        <div>
          <p className={labelClass}>Odds</p>
          <p className={`${valClass} text-[#8ea5c5]`} style={MONO}>
            {oddsStr ?? "—"}
          </p>
        </div>

        {/* CLV — always "—" for today's ungraded picks; honest pending state */}
        <div>
          <p className={labelClass}>CLV</p>
          <p className={`${valClass} text-[#8ea5c5]/40`} style={MONO}>—</p>
          {hero && <p className="text-[9px] text-[#8ea5c5]/30 mt-0.5">pending</p>}
        </div>
      </div>

      {/* ── BUILDING fields ────────────────────────────────────────────── */}
      <div
        className="rounded-lg border border-[#caa024]/12 px-3 py-2"
        style={{ backgroundColor: 'rgba(7,10,16,0.55)' }}
      >
        <p className="mb-1.5 text-[9px] font-bold uppercase tracking-widest text-[#caa024]/45">
          Data Building — show real values once n ≥ {MIN_SAMPLE}
        </p>
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          <div>
            <p className={labelClass}>Hit Rate</p>
            <p className="text-xs text-[#8ea5c5]/65" style={MONO}>
              {buildingValue(gradedN, hitRateStr)}
            </p>
          </div>
          <div>
            <p className={labelClass}>Expected ROI</p>
            <p className="text-xs text-[#8ea5c5]/65" style={MONO}>
              {buildingValue(gradedN, roiStr)}
            </p>
          </div>
          <div>
            <p className={labelClass}>Comparables</p>
            <p className="text-xs text-[#8ea5c5]/50">Building — needs backtest data</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── VerdictPickPanel — dark/gold per-pick market-colored card ────────────────
function VerdictPickPanel({
  pick,
  marketStats,
}: {
  pick: SubPick;
  marketStats: Map<string, MarketGradedStats>;
}) {
  const ms = mktStyle(pick.market);
  const CONDENSED: React.CSSProperties = { fontFamily: "var(--font-condensed, ui-sans-serif)" };

  return (
    <div
      className={`rounded-xl border ${ms.border} px-3 py-3`}
      style={{
        backgroundColor: '#0d1320',
        backgroundImage: 'linear-gradient(rgba(202,160,36,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(202,160,36,0.025) 1px, transparent 1px)',
        backgroundSize: '24px 24px',
      }}
    >
      {/* Market label bar */}
      <div className="mb-2 flex items-center gap-2 flex-wrap">
        <span className={`text-[10px] font-bold uppercase tracking-widest ${ms.textColor}`}>
          {ms.icon} {pick.marketLabel}
        </span>
        {pick.playerName && (
          <span className="text-[10px] text-[#8ea5c5]/55">· {pick.playerName}</span>
        )}
        <GradeChip edge={pick.edge} />
      </div>

      {/* Pick label — Barlow Condensed bold */}
      <p className="mb-3 text-lg font-bold leading-tight text-[#eef7ff]" style={CONDENSED}>
        {pick.label}
      </p>

      {/* Full 9-field set */}
      <PickFieldSet pick={pick} marketStats={marketStats} />
    </div>
  );
}

// ─── VerdictHeroCard — Bet of the Day gold hero block ────────────────────────
function VerdictHeroCard({
  pick,
  marketStats,
  liveState,
}: {
  pick: SubPick;
  marketStats: Map<string, MarketGradedStats>;
  liveState?: Map<string, LiveScore>;
}) {
  const live = liveState?.get(pick.gameId);
  const isLive = live?.isLive ?? false;
  const rationale = buildRationale(pick);
  const CONDENSED: React.CSSProperties = { fontFamily: "var(--font-condensed, ui-sans-serif)" };
  const MONO: React.CSSProperties = { fontFamily: "var(--font-mono-num, ui-monospace)" };

  return (
    <div
      className="rounded-2xl p-5 shadow-2xl"
      style={{
        backgroundColor: '#070a10',
        border: '2px solid #caa024',
        backgroundImage: 'linear-gradient(rgba(202,160,36,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(202,160,36,0.04) 1px, transparent 1px)',
        backgroundSize: '24px 24px',
        boxShadow: '0 0 40px rgba(202,160,36,0.12), 0 8px 32px rgba(0,0,0,0.6)',
      }}
    >
      {/* Badge row */}
      <div className="mb-4 flex items-center gap-2 flex-wrap">
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-extrabold uppercase tracking-widest"
          style={{ border: '1px solid #caa024', backgroundColor: 'rgba(202,160,36,0.15)', color: '#f3c64a' }}
        >
          ★ BET OF THE DAY
        </span>
        {pick.powerScore > 0 && (
          <span className="text-[10px] text-[#8ea5c5]/55" style={MONO}>
            PS {pick.powerScore.toFixed(1)}
          </span>
        )}
        <GradeChip edge={pick.edge} large />
        {isLive && (
          <span className="ml-auto flex items-center gap-1">
            <span className="size-1.5 rounded-full bg-[#f3c64a] animate-pulse" />
            <span className="text-[10px] font-bold text-[#f3c64a] uppercase tracking-wide">Live</span>
          </span>
        )}
      </div>

      {/* Matchup */}
      <div className="mb-1 flex items-center gap-1.5 flex-wrap">
        <TeamLogo team={pick.awayTeam} size={22} />
        <span className="text-sm font-semibold text-[#eef7ff]">{pick.awayTeam}</span>
        <span className="text-[#8ea5c5]/50 text-xs">@</span>
        <TeamLogo team={pick.homeTeam} size={22} />
        <span className="text-sm font-semibold text-[#eef7ff]">{pick.homeTeam}</span>
      </div>
      <p className="mb-4 text-xs text-[#8ea5c5]/60">{formatFirstPitch(pick.gameTime)}</p>

      {/* Market label */}
      <p className="mb-1 text-[10px] font-bold uppercase tracking-widest" style={{ color: '#caa024' }}>
        {pick.marketLabel}{pick.playerName ? ` · ${pick.playerName}` : ""}
      </p>

      {/* Pick label — hero size Barlow Condensed */}
      <p
        className="mb-5 text-4xl font-extrabold leading-tight text-[#eef7ff]"
        style={CONDENSED}
      >
        {pick.label}
      </p>

      {/* Full 9-field set — hero layout */}
      <div
        className="mb-4 rounded-xl border border-[#caa024]/20 px-4 py-4"
        style={{ backgroundColor: 'rgba(13,19,32,0.8)' }}
      >
        <PickFieldSet pick={pick} marketStats={marketStats} hero />
      </div>

      {/* Why we like it */}
      {rationale && (
        <div
          className="mb-4 rounded-lg border border-[#caa024]/15 px-3 py-2.5"
          style={{ backgroundColor: 'rgba(202,160,36,0.04)' }}
        >
          <p className="mb-1 text-[9px] font-bold uppercase tracking-widest text-[#caa024]/50">
            Why we like it
          </p>
          <p className="text-xs text-[#8ea5c5]/80" style={MONO}>{rationale}</p>
        </div>
      )}

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

// ─── VerdictEliteSection ──────────────────────────────────────────────────────
function VerdictEliteSection({
  picks,
  marketStats,
  liveState,
}: {
  picks: SubPick[];
  marketStats: Map<string, MarketGradedStats>;
  liveState?: Map<string, LiveScore>;
}) {
  if (picks.length === 0) return null;

  return (
    <div
      className="rounded-2xl p-4"
      style={{
        backgroundColor: '#0d1320',
        border: '1px solid rgba(167,139,250,0.30)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
      }}
    >
      <div className="mb-3 flex items-center gap-2">
        <span className="inline-flex items-center rounded-full border border-violet-400/50 bg-violet-500/15 px-3 py-1 text-xs font-bold text-violet-300">
          {picks.length} Elite play{picks.length !== 1 ? "s" : ""}
        </span>
        <span className="text-[10px] text-[#8ea5c5]/50">meets BotD bar — not today&apos;s top pick</span>
      </div>

      <div className="flex flex-col gap-3">
        {picks.map((pick) => {
          const live = liveState?.get(pick.gameId);
          const isLive = live?.isLive ?? false;
          return (
            <div
              key={pick.key}
              className="rounded-xl border border-violet-500/20 p-3"
              style={{ backgroundColor: 'rgba(7,10,16,0.7)' }}
            >
              <div className="mb-2 flex items-center gap-1 flex-wrap text-[10px] text-[#8ea5c5]/60">
                <TeamLogo team={pick.awayTeam} size={13} />
                <span className="font-semibold text-[#eef7ff]/80">{pick.awayTeam}</span>
                <span>@</span>
                <TeamLogo team={pick.homeTeam} size={13} />
                <span className="font-semibold text-[#eef7ff]/80">{pick.homeTeam}</span>
                {isLive && (
                  <span className="ml-1 flex items-center gap-0.5">
                    <span className="size-1.5 rounded-full bg-[#f3c64a] animate-pulse" />
                    <span className="font-bold text-[#f3c64a] uppercase">Live</span>
                  </span>
                )}
                <span className="ml-auto">{formatFirstPitch(pick.gameTime)}</span>
              </div>
              <VerdictPickPanel pick={pick} marketStats={marketStats} />
              {live && (
                <div className="mt-2">
                  <LiveScoreModule
                    live={live}
                    market={pick.marketLabel.toLowerCase()}
                    pick={pick.label}
                    homeTeam={pick.homeTeam}
                    awayTeam={pick.awayTeam}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── VerdictGameCard — dark/gold collapsible game card ────────────────────────
function VerdictGameCard({
  group,
  marketStats,
  liveState,
  lineupConfirmed,
  postponedGameIds,
}: {
  group: GameGroup;
  marketStats: Map<string, MarketGradedStats>;
  liveState?: Map<string, LiveScore>;
  lineupConfirmed: boolean;
  postponedGameIds?: Set<string>;
}) {
  const isPostponed = postponedGameIds?.has(group.gameId) ?? false;
  const hasBotD  = !isPostponed && group.picks.some((p) => p.tier === "Bet of the Day");
  const hasElite = !isPostponed && !hasBotD && group.picks.some((p) => p.tier === "Elite");
  const live = liveState?.get(group.gameId);
  const isLive = !isPostponed && (live?.isLive ?? false);

  const nonPropPicks = group.picks.filter((p) => p.source !== "prop");
  const propPicks    = group.picks.filter((p) => p.source === "prop");
  const hasPropPicks = propPicks.length > 0;

  const [open, setOpen] = useState(hasBotD || hasElite || (lineupConfirmed && hasPropPicks));
  const [propsOpen, setPropsOpen] = useState(lineupConfirmed && hasPropPicks);

  const topPick = nonPropPicks[0] ?? propPicks[0];

  // Border: gold for BotD, violet for Elite, dark-muted for others, red-muted for postponed
  const borderStyle: React.CSSProperties = isPostponed
    ? { border: '1px solid rgba(239,68,68,0.25)' }
    : hasBotD
    ? { border: '2px solid #caa024' }
    : hasElite
    ? { border: '1px solid rgba(167,139,250,0.35)' }
    : { border: '1px solid rgba(30,41,59,0.8)' };

  const CONDENSED: React.CSSProperties = { fontFamily: "var(--font-condensed, ui-sans-serif)" };

  return (
    <div
      className="rounded-2xl"
      style={{
        backgroundColor: '#0d1320',
        backgroundImage: 'linear-gradient(rgba(202,160,36,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(202,160,36,0.02) 1px, transparent 1px)',
        backgroundSize: '24px 24px',
        boxShadow: hasBotD
          ? '0 0 20px rgba(202,160,36,0.1), 0 4px 12px rgba(0,0,0,0.5)'
          : '0 4px 12px rgba(0,0,0,0.4)',
        opacity: isPostponed ? 0.7 : 1,
        ...borderStyle,
      }}
    >
      {/* Collapsible header */}
      <button
        className="flex w-full items-start gap-3 px-4 py-3 text-left"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="min-w-0 flex-1">
          {/* Teams */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <TeamLogo team={group.awayTeam} size={18} />
            <span className="text-sm font-bold text-[#eef7ff]" style={CONDENSED}>{group.awayTeam}</span>
            <span className="text-[#8ea5c5]/50 text-[10px]">@</span>
            <TeamLogo team={group.homeTeam} size={18} />
            <span className="text-sm font-bold text-[#eef7ff]" style={CONDENSED}>{group.homeTeam}</span>
          </div>
          {/* Meta row */}
          <div className="mt-0.5 flex items-center gap-2 flex-wrap">
            <p className="text-[11px] text-[#8ea5c5]/60">{formatFirstPitch(group.gameTime)}</p>
            {isPostponed && (
              <span className="inline-flex items-center rounded border border-red-400/40 bg-red-900/30 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-red-400">
                Postponed
              </span>
            )}
            {isLive && (
              <span className="flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-[#f3c64a] animate-pulse" />
                <span className="text-[10px] font-bold text-[#f3c64a] uppercase tracking-wide">Live</span>
              </span>
            )}
            {hasBotD && (
              <span className="text-[10px] font-extrabold text-[#f3c64a]">★ BotD</span>
            )}
            {hasElite && (
              <span className="text-[10px] font-bold text-violet-300">Elite</span>
            )}
            {lineupConfirmed ? (
              <span className="text-[10px] font-semibold text-[#12f38b]">✓ Lineup</span>
            ) : hasPropPicks ? (
              <span className="text-[10px] text-[#8ea5c5]/40">Lineup pending</span>
            ) : null}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2 pt-0.5">
          <span
            className="rounded-full border px-2 py-0.5 text-[10px]"
            style={{ borderColor: 'rgba(202,160,36,0.25)', color: '#8ea5c5', backgroundColor: 'rgba(202,160,36,0.06)' }}
          >
            {group.picks.length}
          </span>
          <span className="text-[10px] text-[#8ea5c5]/40">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {/* Collapsible body */}
      {open && (
        <div
          className="border-t px-4 pb-4 pt-3"
          style={{ borderColor: 'rgba(202,160,36,0.12)' }}
        >
          {nonPropPicks.length > 0 && (
            <div className="flex flex-col gap-2">
              {nonPropPicks.map((pick) => (
                <VerdictPickPanel key={pick.key} pick={pick} marketStats={marketStats} />
              ))}
            </div>
          )}

          {hasPropPicks && (
            <div className={nonPropPicks.length > 0 ? "mt-2" : ""}>
              <button
                onClick={(e) => { e.stopPropagation(); setPropsOpen((o) => !o); }}
                className="flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-left text-[11px] text-[#8ea5c5] transition-colors hover:bg-white/5"
              >
                <span className="flex items-center gap-1.5">
                  <span>⚾ Player Props</span>
                  <span
                    className="rounded-full border px-1.5 py-0.5 text-[10px]"
                    style={{ borderColor: 'rgba(202,160,36,0.25)', color: '#8ea5c5', backgroundColor: 'rgba(202,160,36,0.06)' }}
                  >
                    {propPicks.length}
                  </span>
                  {lineupConfirmed ? (
                    <span className="text-[10px] font-semibold text-[#12f38b]">✓ Lineup confirmed</span>
                  ) : (
                    <span className="text-[10px] text-[#8ea5c5]/45">Lineup pending</span>
                  )}
                </span>
                <span className="shrink-0 text-[#8ea5c5]/50">{propsOpen ? "▲" : "▼"}</span>
              </button>

              {propsOpen && (
                <div className="mt-1.5 flex flex-col gap-2">
                  {propPicks.map((pick) => (
                    <VerdictPickPanel key={pick.key} pick={pick} marketStats={marketStats} />
                  ))}
                </div>
              )}
            </div>
          )}

          {live && topPick && (
            <div className="mt-3">
              <LiveScoreModule
                live={live}
                market={topPick.source === "prop" ? "totals" : topPick.marketLabel.toLowerCase()}
                pick={topPick.label}
                homeTeam={group.homeTeam}
                awayTeam={group.awayTeam}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Subscriber track record ───────────────────────────────────────────────────
function StatCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <p className="text-[10px] text-[#8ea5c5]/55">{label}</p>
      <p className="mt-0.5 text-sm font-bold text-[#eef7ff]">{value}</p>
    </div>
  );
}

function SegmentStats({ label, seg }: { label: string; seg: MLBSubscriberSegment | null }) {
  if (!seg || seg.pickCount === 0) {
    return (
      <div className="flex-1 rounded-xl border border-[#caa024]/15 px-4 py-3 text-center" style={{ backgroundColor: 'rgba(13,19,32,0.8)' }}>
        <p className="text-xs font-semibold text-[#8ea5c5]">{label}</p>
        <p className="mt-1 text-[10px] text-[#8ea5c5]/50">No graded picks yet</p>
      </div>
    );
  }
  const n   = seg.pickCount;
  const wl  = `${seg.winCount}-${seg.lossCount}`;
  const wr  = seg.winRate   != null ? `${(seg.winRate * 100).toFixed(1)}%` : "—";
  const roi = seg.roiPercent != null ? `${seg.roiPercent > 0 ? "+" : ""}${seg.roiPercent.toFixed(1)}%` : "—";
  const edge = seg.avgEdge   != null ? `+${seg.avgEdge.toFixed(1)}%` : "—";
  const prob = seg.avgWinProb != null ? `${seg.avgWinProb.toFixed(1)}%` : "—";
  const clvN = seg.clvSampleCount;
  const clv = clvN >= MIN_CLV_SAMPLE && seg.avgClv != null
    ? `${seg.avgClv > 0 ? "+" : ""}${seg.avgClv.toFixed(2)}% (n=${clvN})`
    : `— (n=${clvN}, building)`;
  const beatRate = clvN >= MIN_CLV_SAMPLE && seg.clvBeatRate != null
    ? `${(seg.clvBeatRate * 100).toFixed(0)}% (n=${clvN})`
    : `— (n=${clvN}, building)`;

  return (
    <div className="flex-1 rounded-xl border border-[#caa024]/15 px-4 py-3" style={{ backgroundColor: 'rgba(13,19,32,0.8)' }}>
      <p className="mb-2 text-center text-xs font-semibold text-[#eef7ff]">{label}</p>
      {n < MIN_SAMPLE && (
        <p className="mb-2 rounded border border-[#caa024]/30 bg-[#caa024]/5 px-2 py-1 text-center text-[10px] text-[#f3c64a]">
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
        <StatCell label="CLV Beat Rate" value={beatRate} />
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
    <div
      className="mt-2 rounded-2xl border border-[#caa024]/15 p-4"
      style={{ backgroundColor: 'rgba(7,10,16,0.85)' }}
    >
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-bold text-[#eef7ff]">Subscriber Track Record</p>
        <span className="rounded-sm bg-[#caa024]/20 px-1.5 py-0.5 text-[9px] font-bold text-[#f3c64a]">
          INTERNAL
        </span>
      </div>

      <p className="mb-3 text-[10px] leading-relaxed text-[#8ea5c5]/70">
        Performance of picks that qualified under the subscriber filter (edge ≥ +{EDGE_MIN}%,
        win prob ≥ {PROB_MIN}%) across all graded game picks and player props.{" "}
        <span className="font-semibold text-[#f3c64a]">CLV is the primary signal.</span>{" "}
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

// ─── Main export ──────────────────────────────────────────────────────────────
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

  // Pre-compute per-market graded stats for "Building (N/30)" gating.
  const marketStats = computeMarketGradedStats(gradedPicks);

  // Lineup confirmation: batter props require lineup submission; pitcher-only does not.
  const lineupConfirmedGameIds = new Set(
    playerProps
      .filter((p) => p.playerType === "batter")
      .map((p) => p.gameId)
  );

  // Compute postponed game IDs from live state.
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

  const { picks: visiblePicks, botdKey } = promoteTiers(filteredRaw, postponedGameIds);

  const botdPick   = botdKey ? visiblePicks.find((p) => p.key === botdKey) ?? null : null;
  const elitePicks = visiblePicks.filter(
    (p) => p.tier === "Elite" && !postponedGameIds.has(p.gameId),
  );

  const groups = buildGroups(visiblePicks);

  return (
    <div className="flex flex-col gap-5">
      {/* Honesty guardrail — restyled for dark theme, never removed */}
      <div
        className="rounded-xl px-4 py-3 text-xs leading-relaxed"
        style={{
          border: '1px solid rgba(202,160,36,0.30)',
          backgroundColor: 'rgba(202,160,36,0.06)',
          color: '#8ea5c5',
        }}
      >
        <span className="font-bold text-[#f3c64a]">INTERNAL — Do not share or bet real money.</span>{" "}
        This is a paper-trading view only. The Poisson model is unproven and still accumulating
        signal. All plays shown are for internal validation. Edge and probability figures are
        model outputs, not verified predictions.
      </div>

      {/* Qualifying criteria legend */}
      <div
        className="rounded-lg px-4 py-2.5 text-xs"
        style={{ border: '1px solid rgba(202,160,36,0.15)', backgroundColor: 'rgba(13,19,32,0.8)', color: '#8ea5c5' }}
      >
        <span className="font-semibold text-[#eef7ff]">Qualifying criteria:</span>{" "}
        Edge ≥ +{EDGE_MIN}% · Win prob ≥ {PROB_MIN}% · No suspect / no-odds flags
        <span className="mx-2 text-[#8ea5c5]/30">·</span>
        <span className="font-semibold text-[#f3c64a]">★ Bet of the Day</span>{" "}
        = top play by Power Score (edge×{PS_EDGE_W} + prob×{PS_PROB_W}), edge ≥ +{BOTD_EDGE}% &amp; prob ≥ {BOTD_PROB}% required
        <span className="mx-2 text-[#8ea5c5]/30">·</span>
        <span className="font-semibold text-violet-300">Elite</span>{" "}
        = BotD-bar met but not selected · Props capped at {MAX_PROPS_PER_GAME} per game
      </div>

      {/* Date selector */}
      <DateSelector dates={dates} selected={dateFilter} onChange={setDateFilter} />

      {/* ★ Bet of the Day — gold hero block */}
      {botdPick && (
        <VerdictHeroCard
          pick={botdPick}
          marketStats={marketStats}
          liveState={liveState}
        />
      )}

      {/* Elite section */}
      <VerdictEliteSection
        picks={elitePicks}
        marketStats={marketStats}
        liveState={liveState}
      />

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
        <div className="flex flex-col gap-3">
          {groups.map((g) => (
            <VerdictGameCard
              key={g.gameId}
              group={g}
              marketStats={marketStats}
              liveState={liveState}
              lineupConfirmed={lineupConfirmedGameIds.has(g.gameId)}
              postponedGameIds={postponedGameIds}
            />
          ))}
        </div>
      )}

      {groups.length > 0 && (
        <p className="text-right text-[10px] text-[#8ea5c5]/40">
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
