"use client";

import { Fragment, useState } from "react";
import type { GradedPick, MarketStats, TrackRecord } from "@/lib/types";
import { EmptyState } from "./EmptyState";

const MARKET_LABELS: Record<string, string> = {
  overall: "Overall",
  goals: "Goal Totals",
  btts: "BTTS",
  winner: "Match Winner",
};

function StatCard({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p
        className={`mt-1.5 text-3xl font-bold tabular-nums ${highlight ? "text-elite" : "text-ink"}`}
      >
        {value}
      </p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </div>
  );
}

function GradeChip({ grade }: { grade: GradedPick["grade"] }) {
  const cls =
    grade === "WIN"
      ? "bg-elite/15 text-elite border-elite/30"
      : grade === "LOSS"
        ? "bg-reject/15 text-reject border-reject/30"
        : "bg-white/5 text-muted border-border-strong";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${cls}`}
    >
      {grade}
    </span>
  );
}

function MarketPickRow({ pick }: { pick: GradedPick }) {
  const score =
    pick.homeScore !== null && pick.awayScore !== null
      ? `${pick.homeScore}–${pick.awayScore}`
      : null;

  const units =
    pick.unitsResult !== null
      ? `${pick.unitsResult > 0 ? "+" : ""}${pick.unitsResult.toFixed(2)}u`
      : null;

  const unitsPositive = pick.unitsResult !== null && pick.unitsResult > 0;

  return (
    <div className="flex items-center gap-3 border-b border-border/40 py-2.5 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium text-ink">
          {pick.homeTeam} <span className="text-muted">vs</span> {pick.awayTeam}
        </p>
        <p className="mt-0.5 text-[11px] text-muted">
          {pick.pick}
          {score && <span className="ml-2 text-muted/60">· {score}</span>}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {pick.noOdds ? (
          <span className="text-[11px] italic text-muted/60">no odds — settled break-even</span>
        ) : pick.oddsDecimal != null ? (
          <span className="text-[11px] text-muted/60">@ {pick.oddsDecimal.toFixed(2)}</span>
        ) : null}
        {units && (
          <span
            className={`text-xs font-semibold tabular-nums ${
              unitsPositive ? "text-elite" : "text-reject"
            }`}
          >
            {units}
          </span>
        )}
        <GradeChip grade={pick.grade} />
      </div>
    </div>
  );
}

function MarketTable({ rows, picks }: { rows: MarketStats[]; picks: GradedPick[] }) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const displayRows = rows.filter((r) => r.market !== "overall");

  const picksByMarket = new Map<string, GradedPick[]>();
  for (const p of picks) {
    const list = picksByMarket.get(p.market) ?? [];
    list.push(p);
    picksByMarket.set(p.market, list);
  }

  if (displayRows.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted">
              Market
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">
              Record
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">
              Win%
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">
              ROI
            </th>
          </tr>
        </thead>
        <tbody>
          {displayRows.map((r) => {
            const isOpen = expanded === r.market;
            const wr = r.winRate !== null ? `${r.winRate.toFixed(1)}%` : "—";
            const roi =
              r.roiPercent !== null
                ? `${r.roiPercent > 0 ? "+" : ""}${r.roiPercent.toFixed(1)}%`
                : "—";
            const roiPositive = r.roiPercent !== null && r.roiPercent > 0;
            const marketPicks = picksByMarket.get(r.market) ?? [];

            return (
              <Fragment key={r.market}>
                <tr
                  className="cursor-pointer border-b border-border last:border-0 hover:bg-white/[0.03]"
                  onClick={() => setExpanded(isOpen ? null : r.market)}
                >
                  <td className="px-5 py-3 font-medium text-ink">
                    <span className="flex items-center gap-2">
                      <span
                        className={`text-[10px] text-muted/50 transition-transform ${isOpen ? "rotate-90" : ""}`}
                      >
                        ▶
                      </span>
                      {MARKET_LABELS[r.market] ?? r.market}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-muted">
                    {r.wins}W / {r.losses}L
                  </td>
                  <td className="px-4 py-3 text-right tabular-nums text-ink">{wr}</td>
                  <td
                    className={`px-4 py-3 text-right tabular-nums font-semibold ${
                      roiPositive
                        ? "text-elite"
                        : r.roiPercent !== null
                          ? "text-reject"
                          : "text-muted"
                    }`}
                  >
                    {roi}
                  </td>
                </tr>
                {isOpen && (
                  <tr className="border-b border-border last:border-0">
                    <td colSpan={4} className="bg-white/[0.015] px-5 pb-3 pt-2">
                      {marketPicks.length === 0 ? (
                        <p className="py-2 text-xs text-muted/60">No settled picks for this market yet.</p>
                      ) : (
                        <div>
                          {marketPicks.map((p) => (
                            <MarketPickRow
                              key={`${p.gameId}-${p.market}-${p.pick}`}
                              pick={p}
                            />
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RecentPickRow({ pick }: { pick: GradedPick }) {
  const units =
    pick.unitsResult !== null
      ? `${pick.unitsResult > 0 ? "+" : ""}${pick.unitsResult.toFixed(2)}u`
      : null;
  const score =
    pick.homeScore !== null && pick.awayScore !== null
      ? `${pick.homeScore}–${pick.awayScore}`
      : null;
  const dateStr = pick.gradedAt
    ? new Intl.DateTimeFormat("en-CA", {
        timeZone: "America/Toronto",
        month: "short",
        day: "numeric",
      }).format(new Date(pick.gradedAt))
    : null;

  return (
    <div className="flex items-center justify-between gap-4 border-b border-border py-3 last:border-0">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-ink">
          {pick.homeTeam} <span className="text-muted">vs</span> {pick.awayTeam}
        </p>
        <p className="mt-0.5 text-xs text-muted">
          {pick.pick}
          {score && <span className="ml-2 text-muted/70">({score})</span>}
          {dateStr && <span className="ml-2 text-muted/50">{dateStr}</span>}
          {pick.noOdds && pick.grade === "WIN" && (
            <span className="ml-2 italic text-muted/60">· no odds — settled break-even</span>
          )}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        {units && (
          <span
            className={`text-sm font-semibold tabular-nums ${
              pick.unitsResult! > 0 ? "text-elite" : "text-reject"
            }`}
          >
            {units}
          </span>
        )}
        <GradeChip grade={pick.grade} />
      </div>
    </div>
  );
}

export function TrackRecordView({ trackRecord }: { trackRecord: TrackRecord }) {
  const { summary, picks } = trackRecord;
  const overall = summary.find((r) => r.market === "overall");

  if (!overall || overall.totalPicks === 0) {
    return (
      <EmptyState
        title="No graded picks yet"
        subtitle="Results show up here once the engine has graded settled matches. Check back after today's games finish."
      />
    );
  }

  const overallWr =
    overall.winRate !== null ? `${overall.winRate.toFixed(1)}%` : "—";
  const overallRoi =
    overall.roiPercent !== null
      ? `${overall.roiPercent > 0 ? "+" : ""}${overall.roiPercent.toFixed(1)}%`
      : "—";

  const recentPicks = picks.slice(0, 25);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border/50 bg-white/[0.02] px-5 py-4 text-xs text-muted/80 leading-relaxed">
        Win rate is not profit. ROI uses the odds each pick was offered at, flat 1-unit stakes.
        Picks published before odds-tracking, or without available odds, settle at break-even (0.00u)
        and are marked accordingly. Click any market row to audit its individual settled picks.
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatCard
          label="Win rate"
          value={overallWr}
          sub={`${overall.wins}W / ${overall.losses}L`}
          highlight={overall.winRate !== null && overall.winRate >= 55}
        />
        <StatCard
          label="ROI"
          value={overallRoi}
          sub={`${overall.totalUnits !== null ? (overall.totalUnits > 0 ? "+" : "") + overall.totalUnits.toFixed(1) : "—"} units`}
          highlight={overall.roiPercent !== null && overall.roiPercent > 0}
        />
        <StatCard
          label="Picks graded"
          value={String(overall.totalPicks)}
          sub="settled matches only"
        />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          By market
        </h2>
        <MarketTable rows={summary} picks={picks} />
      </div>

      {recentPicks.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
            Recent results
          </h2>
          <div className="rounded-2xl border border-border bg-surface px-5">
            {recentPicks.map((p) => (
              <RecentPickRow key={`${p.gameId}-${p.market}-${p.pick}`} pick={p} />
            ))}
          </div>
        </div>
      )}

      <p className="text-center text-xs text-muted/60">
        Settled results only. Wins and losses are both shown. ROI uses 1-unit flat stake.
      </p>
    </div>
  );
}
