import type { MLBMarketStats, MLBTrackRecord } from "@/lib/types";
import { EmptyState } from "./EmptyState";

const MARKET_LABELS: Record<string, string> = {
  moneyline: "Moneyline",
  totals: "Totals",
  run_line: "Run Line",
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
      <p className={`mt-1.5 text-3xl font-bold tabular-nums ${highlight ? "text-elite" : "text-ink"}`}>
        {value}
      </p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </div>
  );
}

function MarketTable({ rows }: { rows: MLBMarketStats[] }) {
  if (rows.length === 0) return null;

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
              Accuracy
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-muted">
              Avg ROI
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const acc = r.accuracy !== null ? `${r.accuracy.toFixed(1)}%` : "—";
            const roi =
              r.roi !== null
                ? `${r.roi > 0 ? "+" : ""}${r.roi.toFixed(1)}%`
                : "—";
            const roiPositive = r.roi !== null && r.roi > 0;

            return (
              <tr key={r.market} className="border-b border-border last:border-0">
                <td className="px-5 py-3 font-medium text-ink">
                  {MARKET_LABELS[r.market] ?? r.market}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-muted">
                  {r.correct}W / {r.incorrect}L
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-ink">{acc}</td>
                <td
                  className={`px-4 py-3 text-right tabular-nums font-semibold ${
                    roiPositive
                      ? "text-elite"
                      : r.roi !== null
                        ? "text-reject"
                        : "text-muted"
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

export function MLBTrackRecordView({ trackRecord }: { trackRecord: MLBTrackRecord }) {
  const { byMarket, totalPredictions, totalCorrect, overallAccuracy, overallRoi } = trackRecord;

  if (totalPredictions === 0) {
    return (
      <EmptyState
        title="No backtest results yet"
        subtitle="Accuracy and ROI figures appear here once the backtest script has run against settled MLB games."
      />
    );
  }

  const accStr = overallAccuracy !== null ? `${overallAccuracy.toFixed(1)}%` : "—";
  const roiStr =
    overallRoi !== null
      ? `${overallRoi > 0 ? "+" : ""}${overallRoi.toFixed(1)}%`
      : "—";

  return (
    <div className="space-y-6">
      {/* Prominent backtest warning — cannot be missed */}
      <div className="rounded-2xl border-2 border-watch/60 bg-watch/10 px-5 py-4 text-sm leading-relaxed text-watch">
        <p className="font-bold text-base mb-1">⚠ BACKTEST ONLY — NOT REAL PERFORMANCE</p>
        <p>
          These figures come from running the model over already-settled games. Backtest results
          are <span className="font-bold">optimistically biased</span>: the model was tuned on
          historical data, so it will look better here than it will in live operation. Do{" "}
          <span className="font-bold">not</span> use these numbers to judge the model.
        </p>
        <p className="mt-2">
          Real forward-looking performance accumulates in the live graded picks.
          Judge the model by <span className="font-bold">live CLV and MAE</span> (visible in
          the Diagnostics tab), not these backtest numbers.
        </p>
      </div>

      <div className="rounded-2xl border border-border/50 bg-white/[0.02] px-5 py-4 text-xs text-muted/80 leading-relaxed">
        Backtested predictions on settled MLB games. Accuracy = correct direction calls / total predictions.
        ROI assumes flat 1-unit stakes at average captured odds. Figures are averages across all backtest runs.
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatCard
          label="Accuracy"
          value={accStr}
          sub={`${totalCorrect}W / ${totalPredictions - totalCorrect}L`}
          highlight={overallAccuracy !== null && overallAccuracy >= 55}
        />
        <StatCard
          label="Avg ROI"
          value={roiStr}
          sub="per backtest run"
          highlight={overallRoi !== null && overallRoi > 0}
        />
        <StatCard
          label="Predictions"
          value={String(totalPredictions)}
          sub="backtested games"
        />
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
          By market
        </h2>
        <MarketTable rows={byMarket} />
      </div>

      <p className="text-center text-xs text-muted/60">
        Backtested results only — live pick grading coming once the season has settled picks.
      </p>
    </div>
  );
}
