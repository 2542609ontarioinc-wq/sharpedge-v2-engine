"use client";

import { useState } from "react";
import type { MLBSharpPick, SharpPick } from "@/lib/types";
import { formatFirstPitch, formatKickoff, formatPercent, formatSignedPercent } from "@/lib/format";
import { Badge, confidenceTierVariant } from "./Badge";
import { ProbabilityBar } from "./ProbabilityBar";

const TIER_ORDER: Record<string, number> = {
  "Bet of the Day": 0,
  Elite: 1,
  Standard: 2,
};

function topTierOf(tiers: (string | null)[]): string | null {
  let best: string | null = null;
  let bestRank = Infinity;
  for (const t of tiers) {
    const rank = t !== null ? (TIER_ORDER[t] ?? 99) : 99;
    if (rank < bestRank) {
      bestRank = rank;
      best = t;
    }
  }
  return best;
}

const MLB_MARKET_LABELS: Record<string, string> = {
  moneyline: "Moneyline",
  totals: "Totals",
  run_line: "Run Line",
};

function formatOdds(decimal: number | null, american: number | null): string | null {
  if (american !== null) return `${american > 0 ? "+" : ""}${american}`;
  if (decimal !== null) return decimal.toFixed(2);
  return null;
}

// ── Soccer ────────────────────────────────────────────────────────────────────

export function SoccerGameGroupCard({ picks }: { picks: SharpPick[] }) {
  const [open, setOpen] = useState(false);
  const first = picks[0];
  const tier = topTierOf(picks.map((p) => p.confidenceTier));
  const isBOD = tier === "Bet of the Day";

  return (
    <div
      className={`rounded-2xl border bg-surface backdrop-blur transition-colors ${
        isBOD ? "border-watch/40" : "border-border hover:border-border-strong"
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full p-5 text-left"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink">
              {first.homeTeam} <span className="text-muted">vs</span> {first.awayTeam}
            </p>
            <p className="mt-0.5 text-xs text-muted">{formatKickoff(first.kickoff)}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="text-xs text-muted">
              {picks.length} pick{picks.length !== 1 ? "s" : ""}
            </span>
            {tier && (
              <Badge variant={confidenceTierVariant(tier)}>
                {isBOD ? "★ " : ""}
                {tier}
              </Badge>
            )}
            <span className="text-xs text-muted">{open ? "▴" : "▾"}</span>
          </div>
        </div>
      </button>

      {open && (
        <div className="border-t border-border px-5 pb-5 pt-4">
          <div className="flex flex-col gap-3">
            {picks.map((pick) => (
              <SoccerPickRow key={pick.market} pick={pick} />
            ))}
          </div>
          <p className="mt-3 text-[10px] leading-snug text-muted/50">
            Internal — tier is confidence-ranked, not proven to win more.
          </p>
        </div>
      )}
    </div>
  );
}

function SoccerPickRow({ pick }: { pick: SharpPick }) {
  return (
    <div className="rounded-xl border border-border bg-bg-2/60 px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <Badge variant="muted">{pick.market}</Badge>
        <div className="flex items-center gap-1.5">
          {pick.confidenceTier && (
            <Badge variant={confidenceTierVariant(pick.confidenceTier)}>
              {pick.confidenceTier === "Bet of the Day" ? "★ " : ""}
              {pick.confidenceTier}
            </Badge>
          )}
          {pick.isRealValue && (
            <Badge variant="elite">{formatSignedPercent(pick.edge)} edge</Badge>
          )}
        </div>
      </div>
      <p className="mb-1 text-base font-semibold text-ink">{pick.pick}</p>
      {pick.bookmaker && (
        <p className="mb-2 text-xs text-muted">via {pick.bookmaker}</p>
      )}
      <div>
        <div className="mb-1 flex items-center justify-between text-xs text-muted">
          <span>Calibrated confidence</span>
          <span className="font-semibold text-ink">{formatPercent(pick.confidence)}</span>
        </div>
        <ProbabilityBar value={pick.confidence} variant="accent" />
      </div>
    </div>
  );
}

// ── MLB ───────────────────────────────────────────────────────────────────────

export function MLBGameGroupCard({ picks }: { picks: MLBSharpPick[] }) {
  const [open, setOpen] = useState(false);
  const first = picks[0];
  const tier = topTierOf(picks.map((p) => p.confidenceTier));
  const isBOD = tier === "Bet of the Day";

  return (
    <div
      className={`rounded-2xl border bg-surface backdrop-blur transition-colors ${
        isBOD ? "border-watch/40" : "border-border hover:border-border-strong"
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full p-5 text-left"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink">
              {first.awayTeam} <span className="text-muted">@</span> {first.homeTeam}
            </p>
            <p className="mt-0.5 text-xs text-muted">{formatFirstPitch(first.gameTime)}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="text-xs text-muted">
              {picks.length} pick{picks.length !== 1 ? "s" : ""}
            </span>
            {tier && (
              <Badge variant={confidenceTierVariant(tier)}>
                {isBOD ? "★ " : ""}
                {tier}
              </Badge>
            )}
            <span className="text-xs text-muted">{open ? "▴" : "▾"}</span>
          </div>
        </div>
      </button>

      {open && (
        <div className="border-t border-border px-5 pb-5 pt-4">
          <div className="flex flex-col gap-3">
            {picks.map((pick) => (
              <MLBPickRow key={pick.market} pick={pick} />
            ))}
          </div>
          <p className="mt-3 text-[10px] leading-snug text-muted/50">
            Internal — tier is confidence-ranked, not proven to win more.
          </p>
        </div>
      )}
    </div>
  );
}

function MLBPickRow({ pick }: { pick: MLBSharpPick }) {
  const oddsStr = formatOdds(pick.oddsDecimal, pick.oddsAmerican);
  const isBOD = pick.confidenceTier === "Bet of the Day";

  return (
    <div className="rounded-xl border border-border bg-bg-2/60 px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <Badge variant="muted">{MLB_MARKET_LABELS[pick.market] ?? pick.market}</Badge>
        <div className="flex items-center gap-1.5">
          {pick.confidenceTier && (
            <Badge variant={confidenceTierVariant(pick.confidenceTier)}>
              {isBOD ? "★ " : ""}
              {pick.confidenceTier}
            </Badge>
          )}
          {pick.isRealValue && (
            <Badge variant="elite">{formatSignedPercent(pick.edge)} edge</Badge>
          )}
        </div>
      </div>
      <p className="mb-1 text-base font-semibold text-ink">{pick.pick}</p>
      {oddsStr && (
        <p className="mb-2 text-xs text-muted">
          {oddsStr}
          {pick.bookmaker && <span className="ml-1.5">via {pick.bookmaker}</span>}
        </p>
      )}
      <div>
        <div className="mb-1 flex items-center justify-between text-xs text-muted">
          <span>Calibrated confidence</span>
          <span className="font-semibold text-ink">
            {formatPercent(pick.calibratedConfidence)}
          </span>
        </div>
        <ProbabilityBar value={pick.calibratedConfidence} variant="accent" />
      </div>
      {pick.secondaryPick && (
        <p className="mt-2 text-xs text-muted/70">
          Also watching:{" "}
          <span className="font-medium text-muted">{pick.secondaryPick}</span>
          {pick.secondaryMarket && (
            <span className="ml-1 text-muted/50">
              ({MLB_MARKET_LABELS[pick.secondaryMarket] ?? pick.secondaryMarket})
            </span>
          )}
        </p>
      )}
    </div>
  );
}
