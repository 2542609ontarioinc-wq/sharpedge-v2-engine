"use client";

import type { MLBDiagnostics, MLBPickDetail, MLBPropDetail } from "@/lib/types";
import { EmptyState } from "./EmptyState";

// Picks need 30+ per bucket before signals are meaningful.
const MIN_RELIABLE = 30;
// Below this in a bucket: "low N" flag but still show data.
const MIN_WATCH_FLAG = 5;

// ── Small utilities ────────────────────────────────────────────────────────

function gradedOnly(picks: MLBPickDetail[]) {
  return picks.filter((p) => p.grade === "WIN" || p.grade === "LOSS");
}

function winCount(picks: MLBPickDetail[]) {
  return gradedOnly(picks).filter((p) => p.grade === "WIN").length;
}

function winRate(picks: MLBPickDetail[]): number | null {
  const g = gradedOnly(picks);
  return g.length > 0 ? winCount(picks) / g.length : null;
}

function roiAvg(picks: MLBPickDetail[]): number | null {
  const g = gradedOnly(picks).filter((p) => !p.noOdds);
  if (g.length === 0) return null;
  return g.reduce((s, p) => s + (p.unitsResult ?? 0), 0) / g.length;
}

function avgBias(picks: MLBPickDetail[]): number | null {
  const g = gradedOnly(picks).filter((p) => p.totalBias !== null);
  if (g.length === 0) return null;
  return g.reduce((s, p) => s + (p.totalBias ?? 0), 0) / g.length;
}

function avgClv(picks: MLBPickDetail[]): number | null {
  const g = picks.filter((p) => p.clv !== null);
  if (g.length === 0) return null;
  return g.reduce((s, p) => s + (p.clv ?? 0), 0) / g.length;
}

function pct(n: number | null, decimals = 1): string {
  if (n === null) return "—";
  return `${(n * 100).toFixed(decimals)}%`;
}

function signed(n: number | null, decimals = 2, suffix = ""): string {
  if (n === null) return "—";
  return `${n > 0 ? "+" : ""}${n.toFixed(decimals)}${suffix}`;
}

// ── Sample-size banner ─────────────────────────────────────────────────────

function SampleBanner({ n, label }: { n: number; label: string }) {
  const ok = n >= MIN_RELIABLE;
  return (
    <div
      className={`rounded-xl border px-5 py-3.5 text-sm leading-relaxed ${
        ok
          ? "border-elite/40 bg-elite/10 text-elite"
          : "border-watch/40 bg-watch/10 text-watch"
      }`}
    >
      <span className="font-bold">
        {label}: N&nbsp;=&nbsp;{n} graded picks.
      </span>{" "}
      {ok ? (
        "Sufficient for initial signals — continue monitoring."
      ) : (
        <>
          <span className="font-bold">INSUFFICIENT DATA</span> — need ~{MIN_RELIABLE}+ per
          bucket for reliable signals. All figures are directional only.
        </>
      )}
    </div>
  );
}

// ── Calibration check ──────────────────────────────────────────────────────

function CalibrationTable({ picks }: { picks: MLBPickDetail[] }) {
  const BUCKETS = ["<55%", "55-65%", "65-75%", "75%+"];

  const rows = BUCKETS.map((bucket) => {
    const inBucket = picks.filter(
      (p) =>
        p.confBucket === bucket &&
        p.calibratedConf !== null &&
        (p.grade === "WIN" || p.grade === "LOSS")
    );
    const n = inBucket.length;
    const wins = inBucket.filter((p) => p.grade === "WIN").length;
    const actualHit = n > 0 ? (wins / n) * 100 : null;
    const avgPred =
      n > 0
        ? inBucket.reduce((s, p) => s + (p.calibratedConf ?? 0), 0) / n
        : null;
    const delta = actualHit !== null && avgPred !== null ? actualHit - avgPred : null;
    return { bucket, n, avgPred, actualHit, delta };
  });

  const hasAnyData = rows.some((r) => r.n > 0);
  if (!hasAnyData) return null;

  return (
    <div>
      <h3 className="mb-1 text-sm font-bold uppercase tracking-wide text-muted">
        Calibration Check
      </h3>
      <p className="mb-3 text-xs text-muted/70">
        A well-calibrated model wins 70% of its 70%-confidence picks. Negative delta = overconfident (primary watch signal).
        Safe-zone picks (no confidence stored) are excluded.
      </p>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {["Confidence Bucket", "N", "Avg Predicted %", "Actual Hit %", "Delta", "Status"].map(
                (h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted"
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const lowN = r.n < MIN_WATCH_FLAG;
              const overconfident = r.delta !== null && r.delta < -5;
              const underconfident = r.delta !== null && r.delta > 5;
              const statusText = lowN
                ? "⚠ low N"
                : overconfident
                ? "WATCH — overconfident"
                : underconfident
                ? "✓ underconfident"
                : r.delta !== null
                ? "✓ calibrated"
                : "—";
              const statusClass = lowN
                ? "text-muted/60"
                : overconfident
                ? "text-watch font-semibold"
                : r.delta !== null
                ? "text-elite"
                : "text-muted";
              return (
                <tr key={r.bucket} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-medium text-ink">{r.bucket}</td>
                  <td className="px-4 py-3 tabular-nums text-muted">{r.n}</td>
                  <td className="px-4 py-3 tabular-nums text-muted">
                    {r.avgPred !== null ? `${r.avgPred.toFixed(1)}%` : "—"}
                  </td>
                  <td className="px-4 py-3 tabular-nums font-semibold text-ink">
                    {r.actualHit !== null ? `${r.actualHit.toFixed(1)}%` : "—"}
                  </td>
                  <td
                    className={`px-4 py-3 tabular-nums font-semibold ${
                      r.delta === null
                        ? "text-muted"
                        : r.delta < -5
                        ? "text-watch"
                        : r.delta > 5
                        ? "text-elite"
                        : "text-muted"
                    }`}
                  >
                    {r.delta !== null ? signed(r.delta / 100, 1, "%") : "—"}
                  </td>
                  <td className={`px-4 py-3 text-xs ${statusClass}`}>{statusText}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Directional bias (totals) ──────────────────────────────────────────────

function DirectionalBias({ picks }: { picks: MLBPickDetail[] }) {
  const totalsPicks = picks.filter(
    (p) =>
      p.market === "totals" &&
      p.modelProjTotal !== null &&
      p.actualTotal !== null &&
      (p.grade === "WIN" || p.grade === "LOSS")
  );
  if (totalsPicks.length === 0) return null;

  const avgProj =
    totalsPicks.reduce((s, p) => s + (p.modelProjTotal ?? 0), 0) /
    totalsPicks.length;
  const avgActual =
    totalsPicks.reduce((s, p) => s + (p.actualTotal ?? 0), 0) /
    totalsPicks.length;
  const bias = avgProj - avgActual;
  const absBias = Math.abs(bias);

  const biasLabel =
    absBias < 0.3
      ? "NEUTRAL — model roughly on target"
      : bias > 0
      ? `TOO HIGH — model over-projects by ${bias.toFixed(2)} runs on average`
      : `TOO LOW — model under-projects by ${absBias.toFixed(2)} runs on average`;

  const biasColor =
    absBias < 0.3 ? "text-elite" : absBias > 1.5 ? "text-watch" : "text-ink";

  return (
    <div>
      <h3 className="mb-1 text-sm font-bold uppercase tracking-wide text-muted">
        Directional Bias — Totals Model
      </h3>
      <p className="mb-3 text-xs text-muted/70">
        Systematic over/under-projection on totals is the clearest model-level error signal. Requires 30+ totals picks.
      </p>
      <div className="rounded-xl border border-border bg-surface px-5 py-5">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted">Avg Model Proj</p>
            <p className="mt-1.5 text-2xl font-bold tabular-nums text-ink">
              {avgProj.toFixed(2)}
            </p>
            <p className="text-xs text-muted">runs</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted">Avg Actual Total</p>
            <p className="mt-1.5 text-2xl font-bold tabular-nums text-ink">
              {avgActual.toFixed(2)}
            </p>
            <p className="text-xs text-muted">runs</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-muted">Net Bias</p>
            <p className={`mt-1.5 text-2xl font-bold tabular-nums ${biasColor}`}>
              {signed(bias, 2)}
            </p>
            <p className="text-xs text-muted">runs</p>
          </div>
        </div>
        <p className={`mt-4 text-center text-sm font-semibold ${biasColor}`}>
          {biasLabel}
        </p>
        <p className="mt-1 text-center text-xs text-muted/70">
          N&nbsp;=&nbsp;{totalsPicks.length} totals picks with projections
          {totalsPicks.length < MIN_RELIABLE && (
            <span className="text-watch">
              {" "}— need {MIN_RELIABLE}+ for reliable bias estimate
            </span>
          )}
        </p>
      </div>
    </div>
  );
}

// ── Breakdown table ────────────────────────────────────────────────────────

type BRow = {
  label: string;
  n: number;
  wins: number;
  losses: number;
  wr: number | null;
  roi: number | null;
  bias: number | null;
  clvVal: number | null;
  watch: boolean;
};

function buildBRow(label: string, subset: MLBPickDetail[]): BRow {
  const g = gradedOnly(subset);
  const wins = g.filter((p) => p.grade === "WIN").length;
  const losses = g.length - wins;
  const wr = g.length > 0 ? wins / g.length : null;
  const roi = roiAvg(subset);
  const bias = avgBias(subset);
  const clvVal = avgClv(subset);
  const watch =
    g.length >= MIN_WATCH_FLAG &&
    ((wr !== null && wr < 0.45) || (bias !== null && Math.abs(bias) > 1.5));
  return { label, n: g.length, wins, losses, wr, roi, bias, clvVal, watch };
}

function BreakdownTable({ rows, title }: { rows: BRow[]; title: string }) {
  const visible = rows.filter((r) => r.n > 0);
  if (visible.length === 0) return null;
  return (
    <div>
      <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-muted">{title}</h3>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {["Segment", "N", "W-L", "W%", "ROI/pick", "Avg Bias", "Avg CLV", ""].map(
                (h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted"
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.label} className="border-b border-border last:border-0">
                <td className="px-4 py-3 font-medium text-ink">{r.label}</td>
                <td className="px-4 py-3 tabular-nums text-muted">{r.n}</td>
                <td className="px-4 py-3 tabular-nums text-muted">
                  {r.wins}W / {r.losses}L
                </td>
                <td
                  className={`px-4 py-3 tabular-nums font-semibold ${
                    r.wr === null
                      ? "text-muted"
                      : r.wr >= 0.53
                      ? "text-elite"
                      : r.wr < 0.45
                      ? "text-reject"
                      : "text-ink"
                  }`}
                >
                  {r.wr !== null ? pct(r.wr) : "—"}
                </td>
                <td
                  className={`px-4 py-3 tabular-nums font-semibold ${
                    r.roi === null
                      ? "text-muted"
                      : r.roi > 0
                      ? "text-elite"
                      : "text-reject"
                  }`}
                >
                  {r.roi !== null ? signed(r.roi * 100, 1, "%") : "—"}
                </td>
                <td
                  className={`px-4 py-3 tabular-nums text-sm ${
                    r.bias === null
                      ? "text-muted"
                      : Math.abs(r.bias) > 1.5
                      ? "text-watch"
                      : "text-muted"
                  }`}
                >
                  {r.bias !== null ? signed(r.bias, 2) : "—"}
                </td>
                <td className="px-4 py-3 tabular-nums text-muted">
                  {r.clvVal !== null ? signed(r.clvVal, 2, "%") : "—"}
                </td>
                <td className="px-4 py-3 text-xs">
                  {r.watch ? (
                    <span className="rounded bg-watch/20 px-2 py-0.5 text-[10px] font-bold text-watch">
                      WATCH
                    </span>
                  ) : r.n < MIN_WATCH_FLAG ? (
                    <span className="text-[10px] text-muted/50">low N</span>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-right text-[10px] text-muted/50">
        W% and ROI are favorites-biased. MAE (Avg Bias) and CLV are the primary signals.
      </p>
    </div>
  );
}

// ── Prop breakdown ─────────────────────────────────────────────────────────

function PropBreakdown({ props }: { props: MLBPropDetail[] }) {
  const MARKETS = [
    "strikeouts",
    "outs_recorded",
    "earned_runs",
    "hits_allowed",
    "walks",
    "h_r_rbi",
  ];

  const rows = MARKETS.map((mkt) => {
    const subset = props.filter((p) => p.propMarket === mkt);
    const g = subset.filter((p) => p.grade === "WIN" || p.grade === "LOSS");
    const wins = g.filter((p) => p.grade === "WIN").length;
    const losses = g.length - wins;
    const wr = g.length > 0 ? wins / g.length : null;
    const biasItems = g.filter((p) => p.propBias !== null);
    const bias =
      biasItems.length > 0
        ? biasItems.reduce((s, p) => s + (p.propBias ?? 0), 0) / biasItems.length
        : null;
    return { mkt, n: g.length, wins, losses, wr, bias };
  }).filter((r) => r.n > 0);

  if (rows.length === 0) return null;

  return (
    <div>
      <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-muted">
        Props — Breakdown by Market
      </h3>
      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {["Market", "N", "W-L", "W%", "Avg Bias (proj−actual)"].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-muted"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.mkt} className="border-b border-border last:border-0">
                <td className="px-4 py-3 font-medium text-ink">{r.mkt}</td>
                <td className="px-4 py-3 tabular-nums text-muted">{r.n}</td>
                <td className="px-4 py-3 tabular-nums text-muted">
                  {r.wins}W / {r.losses}L
                </td>
                <td
                  className={`px-4 py-3 tabular-nums font-semibold ${
                    r.wr === null
                      ? "text-muted"
                      : r.wr >= 0.53
                      ? "text-elite"
                      : r.wr < 0.45
                      ? "text-reject"
                      : "text-ink"
                  }`}
                >
                  {r.wr !== null ? pct(r.wr) : "—"}
                </td>
                <td
                  className={`px-4 py-3 tabular-nums ${
                    r.bias === null
                      ? "text-muted"
                      : Math.abs(r.bias) > 1.0
                      ? "text-watch"
                      : "text-muted"
                  }`}
                >
                  {r.bias !== null ? signed(r.bias, 2) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Per-pick raw detail table ──────────────────────────────────────────────

function PickDetailTable({ picks }: { picks: MLBPickDetail[] }) {
  const sorted = [...picks].sort((a, b) =>
    (b.gameDate ?? "").localeCompare(a.gameDate ?? "")
  );
  return (
    <div>
      <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-muted">
        All Graded Picks — Raw Detail
      </h3>
      <div className="overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="w-full min-w-[950px] text-xs">
          <thead>
            <tr className="border-b border-border">
              {[
                "Date",
                "Game",
                "Market",
                "Pick",
                "Line",
                "Proj Total",
                "Actual",
                "Bias",
                "Conf %",
                "Edge %",
                "Odds",
                "CLV",
                "Grade",
              ].map((h) => (
                <th
                  key={h}
                  className="whitespace-nowrap px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-muted"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((p, i) => {
              const gradeClass =
                p.grade === "WIN"
                  ? "text-elite font-bold"
                  : p.grade === "LOSS"
                  ? "text-reject font-bold"
                  : "text-muted";
              const biasFlag =
                p.totalBias !== null && Math.abs(p.totalBias) > 2;
              return (
                <tr
                  key={i}
                  className="border-b border-border last:border-0 hover:bg-white/[0.02]"
                >
                  <td className="whitespace-nowrap px-3 py-2 text-muted">
                    {p.gameDate ?? "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-ink">
                    {p.awayTeam} @ {p.homeTeam}
                  </td>
                  <td className="px-3 py-2 text-muted">{p.market}</td>
                  <td className="px-3 py-2 text-ink">{p.pick}</td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.pickLine !== null ? p.pickLine : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.modelProjTotal !== null ? p.modelProjTotal.toFixed(1) : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums font-semibold text-ink">
                    {p.actualTotal !== null ? p.actualTotal : "—"}
                  </td>
                  <td
                    className={`px-3 py-2 tabular-nums font-semibold ${
                      p.totalBias === null
                        ? "text-muted"
                        : biasFlag
                        ? "text-watch"
                        : "text-muted"
                    }`}
                  >
                    {p.totalBias !== null ? signed(p.totalBias, 1) : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.calibratedConf !== null
                      ? `${p.calibratedConf.toFixed(1)}%`
                      : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.modelEdge !== null ? signed(p.modelEdge, 1, "%") : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.oddsDecimal !== null ? p.oddsDecimal.toFixed(2) : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.clv !== null ? signed(p.clv, 2, "%") : "—"}
                  </td>
                  <td className={`px-3 py-2 ${gradeClass}`}>{p.grade ?? "—"}</td>
                </tr>
              );
            })}
            {sorted.length === 0 && (
              <tr>
                <td
                  colSpan={13}
                  className="px-4 py-8 text-center text-sm text-muted"
                >
                  No graded picks yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Per-prop raw detail table ──────────────────────────────────────────────

function PropDetailTable({ props }: { props: MLBPropDetail[] }) {
  if (props.length === 0) return null;
  const sorted = [...props].sort((a, b) =>
    (b.gameDate ?? "").localeCompare(a.gameDate ?? "")
  );
  return (
    <div>
      <h3 className="mb-3 text-sm font-bold uppercase tracking-wide text-muted">
        All Graded Props — Raw Detail
      </h3>
      <div className="overflow-x-auto rounded-xl border border-border bg-surface">
        <table className="w-full min-w-[820px] text-xs">
          <thead>
            <tr className="border-b border-border">
              {[
                "Date",
                "Player",
                "Type",
                "Market",
                "Side",
                "Line",
                "Proj",
                "Actual",
                "Bias",
                "Cal Prob",
                "Odds",
                "Grade",
              ].map((h) => (
                <th
                  key={h}
                  className="whitespace-nowrap px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wide text-muted"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((p, i) => {
              const gradeClass =
                p.grade === "WIN"
                  ? "text-elite font-bold"
                  : p.grade === "LOSS"
                  ? "text-reject font-bold"
                  : "text-muted";
              return (
                <tr
                  key={i}
                  className="border-b border-border last:border-0 hover:bg-white/[0.02]"
                >
                  <td className="whitespace-nowrap px-3 py-2 text-muted">
                    {p.gameDate ?? "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-ink">
                    {p.playerName ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-muted">{p.playerType ?? "—"}</td>
                  <td className="px-3 py-2 text-muted">{p.propMarket}</td>
                  <td className="px-3 py-2 text-ink">{p.pickSide ?? "—"}</td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.marketLine !== null ? p.marketLine : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.modelProjection !== null ? p.modelProjection.toFixed(1) : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums font-semibold text-ink">
                    {p.actualValue !== null ? p.actualValue.toFixed(1) : "—"}
                  </td>
                  <td
                    className={`px-3 py-2 tabular-nums ${
                      p.propBias === null
                        ? "text-muted"
                        : Math.abs(p.propBias) > 1.5
                        ? "text-watch"
                        : "text-muted"
                    }`}
                  >
                    {p.propBias !== null ? signed(p.propBias, 1) : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.calibratedProb !== null
                      ? `${p.calibratedProb.toFixed(1)}%`
                      : "—"}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted">
                    {p.bestOddsDecimal !== null ? p.bestOddsDecimal.toFixed(2) : "—"}
                  </td>
                  <td className={`px-3 py-2 ${gradeClass}`}>{p.grade ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Main export ────────────────────────────────────────────────────────────

export function MLBDiagnosticsView({ data }: { data: MLBDiagnostics }) {
  const { picks, props } = data;

  const N = gradedOnly(picks).length;
  const Nprop = props.filter((p) => p.grade === "WIN" || p.grade === "LOSS").length;

  if (picks.length === 0 && props.length === 0) {
    return (
      <EmptyState
        title="No graded data yet"
        subtitle="Diagnostics appear once games settle and the grader has run. Run sql/086_mlb_pick_detail.sql in Supabase first."
      />
    );
  }

  // Breakdown segments — game picks only
  const MARKETS = ["moneyline", "totals", "run_line", "safe_balanced", "safe_banker"];
  const EDGE_BUCKETS = ["<2%", "2-5%", "5%+"];
  const CONF_BUCKETS = ["<55%", "55-65%", "65-75%", "75%+"];

  const marketRows = MARKETS.map((m) =>
    buildBRow(m, picks.filter((p) => p.market === m))
  );
  const edgeRows = EDGE_BUCKETS.map((b) =>
    buildBRow(`Edge ${b}`, picks.filter((p) => p.edgeBucket === b))
  );
  const confRows = CONF_BUCKETS.map((b) =>
    buildBRow(b, picks.filter((p) => p.confBucket === b && p.calibratedConf !== null))
  );

  return (
    <div className="space-y-8">
      {/* Diagnostic-only disclaimer */}
      <div className="rounded-xl border border-border/50 bg-white/[0.02] px-5 py-4 text-xs leading-relaxed text-muted/80">
        <span className="font-bold text-watch">DIAGNOSTIC LAYER — INTERNAL ONLY.</span>{" "}
        Nothing here changes picks, weights, or model output. Win% and ROI are favorites-biased
        and are secondary signals. MAE (Avg Bias on totals), calibration delta, and CLV are the
        primary diagnostic signals — but all require 30+ samples per bucket to be meaningful.
      </div>

      {/* Sample-size banners */}
      <div className="space-y-2">
        <SampleBanner n={N} label="Game picks" />
        {Nprop > 0 && <SampleBanner n={Nprop} label="Prop picks" />}
      </div>

      {/* Calibration check */}
      <CalibrationTable picks={picks} />

      {/* Directional bias */}
      <DirectionalBias picks={picks} />

      {/* Breakdowns */}
      <BreakdownTable rows={marketRows} title="Breakdown by Market" />
      <BreakdownTable rows={edgeRows} title="Breakdown by Edge Bucket" />
      <BreakdownTable rows={confRows} title="Breakdown by Confidence Bucket" />

      {/* Props */}
      <PropBreakdown props={props} />

      {/* Raw pick detail */}
      <PickDetailTable picks={picks} />
      <PropDetailTable props={props} />
    </div>
  );
}
