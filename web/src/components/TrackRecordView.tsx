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

function MarketTable({ rows }: { rows: MarketStats[] }) {
  const displayRows = rows.filter((r) => r.market !== "overall");
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
            const wr = r.winRate !== null ? `${r.winRate.toFixed(1)}%` : "—";
            const roi = r.roiPercent !== null ? `${r.roiPercent > 0 ? "+" : ""}${r.roiPercent.toFixed(1)}%` : "—";
            const roiPositive = r.roiPercent !== null && r.roiPercent > 0;

            return (
              <tr
                key={r.market}
                className="border-b border-border last:border-0 hover:bg-white/[0.02]"
              >
                <td className="px-5 py-3 font-medium text-ink">
                  {MARKET_LABELS[r.market] ?? r.market}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-muted">
                  {r.wins}W / {r.losses}L
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-ink">{wr}</td>
                <td
                  className={`px-4 py-3 text-right tabular-nums font-semibold ${
                    roiPositive ? "text-elite" : r.roiPercent !== null ? "text-reject" : "text-muted"
                  }`}
                >
                  {roi}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
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
  const { summary, recentPicks } = trackRecord;
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

  return (
    <div className="space-y-6">
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
        <MarketTable rows={summary} />
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
