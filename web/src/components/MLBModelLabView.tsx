"use client";

import { useState } from "react";
import type { MLBModelAnalytics, MLBModelLabGame, MLBModelVersionData } from "@/lib/types";
import { formatFirstPitch } from "@/lib/format";
import { EmptyState } from "./EmptyState";
import { DateSelector } from "./DateSelector";

const MODEL_ORDER = [
  "poisson_v2",
  "poisson_v3_bullpen",
  "poisson_v4_lineup",
  "poisson_v5_environment",
  "poisson_v6_form",
  "poisson_v7_statcast",
] as const;

const MODEL_META: Record<string, { short: string; feature: string; prod: boolean }> = {
  poisson_v2:             { short: "v2", feature: "Base Poisson",  prod: true  },
  poisson_v3_bullpen:     { short: "v3", feature: "Bullpen",        prod: false },
  poisson_v4_lineup:      { short: "v4", feature: "Lineup",         prod: false },
  poisson_v5_environment: { short: "v5", feature: "Park+Weather",   prod: false },
  poisson_v6_form:        { short: "v6", feature: "Recent Form",    prod: false },
  poisson_v7_statcast:    { short: "v7", feature: "Statcast",       prod: false },
};

const MARKET_SHORT: Record<string, string> = {
  moneyline: "ML",
  totals: "O/U",
  run_line: "RL",
};

function overUnderLean(m: MLBModelVersionData): "Over" | "Under" | null {
  if (m.over85Prob == null) return null;
  return m.over85Prob > 50 ? "Over" : "Under";
}

function pct(fraction: number | null, decimals = 1): string {
  if (fraction == null) return "—";
  return `${(fraction * 100).toFixed(decimals)}%`;
}

function fmt(n: number | null, decimals = 3): string {
  if (n == null) return "—";
  return n.toFixed(decimals);
}

function roiFmt(n: number | null): string {
  if (n == null) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
}

// ─── MODEL SCOREBOARD ────────────────────────────────────────────────────────

function ModelScoreboard({ analytics }: { analytics: MLBModelAnalytics[] }) {
  // Sort by MAE ascending, null-last; fall back to MODEL_ORDER for ties/nulls
  const sorted = [...analytics].sort((a, b) => {
    if (a.mae == null && b.mae == null) {
      return MODEL_ORDER.indexOf(a.modelVersion as typeof MODEL_ORDER[number]) -
             MODEL_ORDER.indexOf(b.modelVersion as typeof MODEL_ORDER[number]);
    }
    if (a.mae == null) return 1;
    if (b.mae == null) return -1;
    return a.mae - b.mae;
  });

  // Fill in any models not yet in the analytics table (no row yet = zero games graded)
  const present = new Set(sorted.map((r) => r.modelVersion));
  const placeholder: MLBModelAnalytics[] = MODEL_ORDER
    .filter((ver) => !present.has(ver))
    .map((ver) => ({
      modelVersion: ver,
      gamesGraded: 0,
      mae: null,
      brierScore: null,
      directionAccuracy: null,
      winRate: null,
      roiPercent: null,
      avgClv: null,
    }));
  const rows = [...sorted, ...placeholder];

  const totalGraded = rows.reduce((s, r) => s + r.gamesGraded, 0);

  return (
    <section>
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h3 className="text-sm font-bold text-ink">Model Scoreboard</h3>
        <span className="text-[11px] text-muted/60">sorted by MAE ↓ (lower = better)</span>
      </div>

      {totalGraded === 0 && (
        <div className="mb-3 rounded-lg border border-border-strong/40 bg-bg-2/60 px-4 py-2.5 text-xs text-muted">
          Accumulating — <span className="font-semibold text-ink">0 games graded so far.</span>{" "}
          Scoreboard metrics appear once results are settled and graded by the engine.
        </div>
      )}
      {totalGraded > 0 && totalGraded < 10 && (
        <div className="mb-3 rounded-lg border border-border/40 bg-bg-2/60 px-4 py-2.5 text-xs text-muted">
          Accumulating — <span className="font-semibold text-ink">{totalGraded} game{totalGraded !== 1 ? "s" : ""} graded so far.</span>{" "}
          MAE and CLV need ~30+ games to stabilize.
        </div>
      )}

      <div className="-mx-1 overflow-x-auto px-1">
        <table className="min-w-full border-collapse text-xs">
          <thead>
            <tr className="border-b border-border/50">
              <th className="py-2 pr-3 text-left font-semibold text-muted/80">Model</th>
              {/* Primary columns get accent underline via border-bottom trick */}
              <th className="min-w-[68px] border-b-2 border-accent/40 px-2 py-2 text-right font-bold text-accent">
                MAE ↓ ★
              </th>
              <th className="min-w-[56px] px-2 py-2 text-right font-semibold text-muted/80">Brier ↓</th>
              <th className="min-w-[56px] px-2 py-2 text-right font-semibold text-muted/80">Dir.%</th>
              <th className="min-w-[60px] px-2 py-2 text-right font-semibold text-muted/80">
                Win% <span className="text-watch/70">⚠</span>
              </th>
              <th className="min-w-[56px] px-2 py-2 text-right font-semibold text-muted/80">
                ROI <span className="text-watch/70">⚠</span>
              </th>
              <th className="min-w-[60px] border-b-2 border-elite/40 px-2 py-2 text-right font-bold text-elite">
                CLV ★
              </th>
              <th className="min-w-[36px] px-2 py-2 text-right font-semibold text-muted/80">N</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/20">
            {rows.map((row) => {
              const meta = MODEL_META[row.modelVersion];
              const hasData = row.gamesGraded > 0;
              return (
                <tr
                  key={row.modelVersion}
                  className={`transition-colors ${meta?.prod ? "bg-accent/3" : ""}`}
                >
                  {/* Model name + badges */}
                  <td className="py-2.5 pr-3">
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-ink">{meta?.short ?? row.modelVersion}</span>
                        <span className="text-[10px] text-muted/60">{meta?.feature}</span>
                      </div>
                      {meta?.prod ? (
                        <span className="w-fit rounded bg-accent/15 px-1.5 py-px text-[9px] font-bold tracking-wide text-accent">
                          PRODUCTION (live)
                        </span>
                      ) : (
                        <span className="w-fit rounded bg-border-strong/20 px-1.5 py-px text-[9px] font-medium text-muted/50">
                          SHADOW
                        </span>
                      )}
                    </div>
                  </td>

                  {/* MAE — primary judge */}
                  <td className={`px-2 py-2.5 text-right font-mono font-bold ${hasData && row.mae != null ? "text-accent" : "text-muted/30"}`}>
                    {fmt(row.mae, 3)}
                  </td>

                  {/* Brier score */}
                  <td className={`px-2 py-2.5 text-right font-mono ${hasData ? "text-ink" : "text-muted/30"}`}>
                    {fmt(row.brierScore, 3)}
                  </td>

                  {/* Direction accuracy */}
                  <td className={`px-2 py-2.5 text-right font-mono ${hasData ? "text-ink" : "text-muted/30"}`}>
                    {pct(row.directionAccuracy, 0)}
                  </td>

                  {/* Win-rate (secondary — fraction × 100) */}
                  <td className={`px-2 py-2.5 text-right font-mono ${hasData ? "text-ink" : "text-muted/30"}`}>
                    {pct(row.winRate, 0)}
                  </td>

                  {/* ROI (secondary — already a %) */}
                  <td className={`px-2 py-2.5 text-right font-mono ${
                    !hasData || row.roiPercent == null
                      ? "text-muted/30"
                      : row.roiPercent >= 0
                      ? "text-elite"
                      : "text-reject"
                  }`}>
                    {roiFmt(row.roiPercent)}
                  </td>

                  {/* CLV — primary judge */}
                  <td className={`px-2 py-2.5 text-right font-mono font-bold ${
                    !hasData || row.avgClv == null
                      ? "text-muted/30"
                      : row.avgClv >= 0
                      ? "text-elite"
                      : "text-reject"
                  }`}>
                    {row.avgClv != null ? `${row.avgClv >= 0 ? "+" : ""}${row.avgClv.toFixed(2)}` : "—"}
                  </td>

                  {/* Games graded */}
                  <td className="px-2 py-2.5 text-right font-mono text-muted/70">
                    {row.gamesGraded}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-2 text-[10px] leading-snug text-muted/45">
        ★ MAE and CLV are the primary promotion judges — evaluated over weeks, not days.{" "}
        <span className="text-watch/60">⚠</span> Win-rate and ROI are subject to favorites bias and are not a promotion signal alone.
      </p>
    </section>
  );
}

// ─── MAIN VIEW ───────────────────────────────────────────────────────────────

function gameDate(g: MLBModelLabGame): string | null {
  if (!g.gameTime) return null;
  const d = new Date(g.gameTime);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto" }).format(d);
}

export function MLBModelLabView({
  games,
  analytics,
}: {
  games: MLBModelLabGame[];
  analytics: MLBModelAnalytics[];
}) {
  const [dateFilter, setDateFilter] = useState("all");

  const gameDates = [...new Set(
    games.map(gameDate).filter(Boolean) as string[]
  )].sort();

  const filteredGames =
    dateFilter === "all"
      ? games
      : games.filter((g) => gameDate(g) === dateFilter);

  const divergentCount = filteredGames.filter((g) => g.hasDisagreement).length;

  return (
    <div className="flex flex-col gap-6">
      {/* Honesty banner */}
      <div className="rounded-xl border border-watch/25 bg-watch/5 px-4 py-3 text-xs leading-relaxed text-muted">
        <span className="font-bold text-watch">INTERNAL — Model Lab</span>
        <span className="mx-2 text-muted/40">|</span>
        Shadow models (v3–v7) are unproven and accumulate signal over weeks.
        They are judged by CLV and MAE, not driving real picks.{" "}
        <span className="font-semibold text-accent">v2 is the only live production model.</span>
        {divergentCount > 0 && (
          <span className="ml-2 font-semibold text-watch">
            {divergentCount} game{divergentCount !== 1 ? "s" : ""} with model divergence
            {dateFilter !== "all" ? " on selected date" : " today"}.
          </span>
        )}
      </div>

      {/* Section A: Model Scoreboard */}
      <div className="rounded-2xl border border-border bg-surface p-4 backdrop-blur">
        <ModelScoreboard analytics={analytics} />
      </div>

      {/* Section B: Game picks by model */}
      <section>
        <h3 className="mb-3 text-sm font-bold text-ink">
          Today&rsquo;s Picks by Model
          <span className="ml-2 text-[11px] font-normal text-muted/60">
            — highlighted cells disagree with v2
          </span>
        </h3>

        <DateSelector dates={gameDates} selected={dateFilter} onChange={setDateFilter} />

        {filteredGames.length === 0 ? (
          <EmptyState
            title="No model lab data yet"
            subtitle={
              dateFilter !== "all"
                ? "No games on the selected date. Try a different date or select 'All dates'."
                : "Run the engine to generate today's multi-version predictions. All six model versions write to mlb_run_predictions and mlb_model_picks."
            }
          />
        ) : (
          <div className="flex flex-col gap-4">
            {filteredGames.map((game) => (
              <GameLabCard key={game.gameId} game={game} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

// ─── PER-GAME CARD ────────────────────────────────────────────────────────────

function GameLabCard({ game }: { game: MLBModelLabGame }) {
  const v2 = game.models["poisson_v2"];
  const v2Total = v2?.expectedTotalRuns ?? null;
  const v2Lean = v2 ? overUnderLean(v2) : null;

  const missingModels = MODEL_ORDER.filter((v) => v !== "poisson_v2" && !game.models[v]);

  return (
    <div
      className={`rounded-2xl border bg-surface p-4 backdrop-blur transition-colors ${
        game.hasDisagreement ? "border-watch/35" : "border-border"
      }`}
    >
      {/* Game header */}
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-ink">
            {game.awayTeam} <span className="text-muted">@</span> {game.homeTeam}
          </p>
          <p className="mt-0.5 text-xs text-muted">{formatFirstPitch(game.gameTime)}</p>
        </div>
        {game.hasDisagreement && (
          <span className="shrink-0 rounded-full border border-watch/40 bg-watch/10 px-2.5 py-0.5 text-xs font-bold text-watch">
            Models diverge
          </span>
        )}
      </div>

      {/* Model comparison table */}
      <div className="-mx-1 overflow-x-auto px-1">
        <table className="min-w-full border-collapse">
          <thead>
            <tr>
              <th className="w-24 py-1.5 pr-3 text-left align-bottom" />
              {MODEL_ORDER.map((ver) => {
                const meta = MODEL_META[ver];
                const present = Boolean(game.models[ver]);
                return (
                  <th
                    key={ver}
                    className={`min-w-[96px] px-2 py-1.5 text-center align-bottom text-xs ${
                      !present ? "opacity-25" : ""
                    }`}
                  >
                    <div className="flex flex-col items-center gap-1">
                      <span className="font-bold text-ink">{meta.short}</span>
                      <span className="text-[10px] font-normal text-muted/70">{meta.feature}</span>
                      {meta.prod ? (
                        <span className="rounded bg-accent/15 px-1.5 py-px text-[9px] font-bold tracking-wide text-accent">
                          PROD
                        </span>
                      ) : (
                        <span className="rounded bg-border-strong/30 px-1.5 py-px text-[9px] font-medium text-muted/50">
                          SHADOW
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>

          <tbody className="divide-y divide-border/30">
            {/* Best pick (from mlb_model_picks) */}
            <PickRow v2={v2} models={game.models} />

            {/* Expected total runs */}
            <tr>
              <td className="py-2.5 pr-3 text-xs text-muted/80">Exp. total</td>
              {MODEL_ORDER.map((ver) => {
                const m = game.models[ver];
                if (!m) return <td key={ver} className="py-2.5 px-2 text-center text-xs text-muted/25">—</td>;
                const total = m.expectedTotalRuns;
                const diff =
                  v2Total != null && total != null && ver !== "poisson_v2"
                    ? total - v2Total
                    : null;
                const flagged = diff != null && Math.abs(diff) > 0.5;
                return (
                  <td
                    key={ver}
                    className={`py-2.5 px-2 text-center text-xs font-mono ${
                      flagged ? "font-bold text-watch" : "text-ink"
                    }`}
                  >
                    {total != null ? total.toFixed(2) : "—"}
                    {flagged && diff != null && (
                      <span className="ml-1 text-[10px] text-watch/70">
                        ({diff > 0 ? "+" : ""}{diff.toFixed(1)})
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>

            {/* O/U lean at 8.5 */}
            <tr>
              <td className="py-2.5 pr-3 text-xs text-muted/80">
                O/U lean
                <span className="ml-1 text-[10px] text-muted/40">@8.5</span>
              </td>
              {MODEL_ORDER.map((ver) => {
                const m = game.models[ver];
                if (!m) return <td key={ver} className="py-2.5 px-2 text-center text-xs text-muted/25">—</td>;
                const l = overUnderLean(m);
                const flipped = l != null && v2Lean != null && l !== v2Lean && ver !== "poisson_v2";
                return (
                  <td key={ver} className="py-2.5 px-2 text-center text-xs">
                    {l ? (
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          flipped
                            ? "border border-watch/50 bg-watch/15 text-watch"
                            : l === "Over"
                            ? "bg-elite/10 text-elite"
                            : "bg-accent-2/10 text-accent-2"
                        }`}
                      >
                        {l}
                        {m.over85Prob != null && (
                          <span className="ml-1 font-normal opacity-60">
                            {m.over85Prob.toFixed(0)}%
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-muted/25">—</span>
                    )}
                  </td>
                );
              })}
            </tr>

            {/* Home win probability */}
            <tr>
              <td className="py-2.5 pr-3 text-xs text-muted/80">Home win</td>
              {MODEL_ORDER.map((ver) => {
                const m = game.models[ver];
                if (!m) return <td key={ver} className="py-2.5 px-2 text-center text-xs text-muted/25">—</td>;
                return (
                  <td key={ver} className="py-2.5 px-2 text-center font-mono text-xs text-ink">
                    {m.homeWinProb != null ? `${m.homeWinProb.toFixed(0)}%` : "—"}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>

      {missingModels.length > 0 && (
        <p className="mt-3 text-[10px] leading-snug text-muted/40">
          — = not yet run (e.g. lineup not confirmed → v4 unavailable)
        </p>
      )}
    </div>
  );
}

// Separate component for the "Best pick" row to keep GameLabCard readable
function PickRow({
  models,
  v2,
}: {
  v2: MLBModelVersionData | undefined;
  models: Record<string, MLBModelVersionData>;
}) {
  const v2Pick = v2?.bestPick ?? null;
  const v2Market = v2?.market ?? null;

  // If no model has a pick yet, skip the row entirely
  const anyPick = MODEL_ORDER.some((ver) => models[ver]?.bestPick != null);
  if (!anyPick) return null;

  return (
    <tr>
      <td className="py-2.5 pr-3 text-xs font-semibold text-muted/80">Sharp pick</td>
      {MODEL_ORDER.map((ver) => {
        const m = models[ver];
        if (!m) {
          return (
            <td key={ver} className="py-2.5 px-2 text-center text-xs text-muted/25">
              —
            </td>
          );
        }

        if (!m.bestPick) {
          // Model exists (has run data) but no pick — e.g. lineup missing for v4
          const meta = MODEL_META[ver];
          const missingReason =
            ver === "poisson_v4_lineup" ? "no lineup yet"
            : ver === "poisson_v7_statcast" ? "no statcast"
            : "no pick";
          return (
            <td key={ver} className="py-2.5 px-2 text-center text-[10px] italic text-muted/35">
              {missingReason}
            </td>
          );
        }

        const marketLabel = m.market ? (MARKET_SHORT[m.market] ?? m.market) : null;
        const isDivergent =
          ver !== "poisson_v2" &&
          v2Pick != null &&
          v2Market != null &&
          m.market === v2Market &&
          m.bestPick !== v2Pick;

        return (
          <td key={ver} className="py-2.5 px-2 text-center text-xs">
            <span
              className={`inline-flex flex-col items-center gap-0.5 ${
                isDivergent ? "font-bold text-watch" : "text-ink"
              }`}
            >
              <span>{m.bestPick}</span>
              {marketLabel && (
                <span className={`text-[10px] ${isDivergent ? "text-watch/70" : "text-muted/50"}`}>
                  {marketLabel}
                  {isDivergent && (
                    <span className="ml-1 rounded-full border border-watch/50 bg-watch/10 px-1 py-px text-[9px]">
                      ≠ v2
                    </span>
                  )}
                </span>
              )}
            </span>
          </td>
        );
      })}
    </tr>
  );
}
