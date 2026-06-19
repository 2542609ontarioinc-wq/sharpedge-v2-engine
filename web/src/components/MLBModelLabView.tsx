import type { MLBModelLabGame, MLBModelVersionData } from "@/lib/types";
import { formatFirstPitch } from "@/lib/format";
import { EmptyState } from "./EmptyState";

const MODEL_ORDER = [
  "poisson_v2",
  "poisson_v3_bullpen",
  "poisson_v4_lineup",
  "poisson_v5_environment",
  "poisson_v6_form",
  "poisson_v7_statcast",
] as const;

const MODEL_META: Record<string, { short: string; feature: string; prod: boolean }> = {
  poisson_v2:            { short: "v2", feature: "Base Poisson",   prod: true  },
  poisson_v3_bullpen:    { short: "v3", feature: "Bullpen",         prod: false },
  poisson_v4_lineup:     { short: "v4", feature: "Lineup",          prod: false },
  poisson_v5_environment:{ short: "v5", feature: "Park + Weather",  prod: false },
  poisson_v6_form:       { short: "v6", feature: "Recent Form",     prod: false },
  poisson_v7_statcast:   { short: "v7", feature: "Statcast",        prod: false },
};

function lean(m: MLBModelVersionData): "Over" | "Under" | null {
  if (m.over85Prob == null) return null;
  return m.over85Prob > 50 ? "Over" : "Under";
}

export function MLBModelLabView({ games }: { games: MLBModelLabGame[] }) {
  if (games.length === 0) {
    return (
      <EmptyState
        title="No model lab data yet"
        subtitle="Run the engine to generate today's multi-version predictions. All six model versions write to mlb_run_predictions."
      />
    );
  }

  const divergentCount = games.filter((g) => g.hasDisagreement).length;

  return (
    <div className="flex flex-col gap-4">
      {/* Honesty banner */}
      <div className="rounded-xl border border-watch/25 bg-watch/5 px-4 py-3 text-xs leading-relaxed text-muted">
        <span className="font-bold text-watch">INTERNAL — Model Lab</span>
        <span className="mx-2 text-muted/40">|</span>
        Shadow models (v3–v7) are unproven and accumulate signal over weeks.
        They are judged by CLV and backtest, not driving real picks.{" "}
        <span className="font-semibold text-accent">v2 is the only live production model.</span>
        {divergentCount > 0 && (
          <span className="ml-2 font-semibold text-watch">
            {divergentCount} game{divergentCount !== 1 ? "s" : ""} with model divergence today.
          </span>
        )}
      </div>

      {games.map((game) => <GameLabCard key={game.gameId} game={game} />)}
    </div>
  );
}

function GameLabCard({ game }: { game: MLBModelLabGame }) {
  const v2 = game.models["poisson_v2"];
  const v2Total = v2?.expectedTotalRuns ?? null;
  const v2Lean = v2 ? lean(v2) : null;

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

      {/* Model comparison table — scrolls horizontally on narrow screens */}
      <div className="-mx-1 overflow-x-auto px-1">
        <table className="min-w-full border-collapse">
          <thead>
            <tr>
              {/* Row-label column */}
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
            {/* Expected total runs */}
            <tr>
              <td className="py-2.5 pr-3 text-xs text-muted/80">Exp. total</td>
              {MODEL_ORDER.map((ver) => {
                const m = game.models[ver];
                if (!m) {
                  return (
                    <td key={ver} className="py-2.5 px-2 text-center text-xs text-muted/25">
                      —
                    </td>
                  );
                }
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
                        ({diff > 0 ? "+" : ""}
                        {diff.toFixed(1)})
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
                if (!m) {
                  return (
                    <td key={ver} className="py-2.5 px-2 text-center text-xs text-muted/25">
                      —
                    </td>
                  );
                }
                const l = lean(m);
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
                if (!m) {
                  return (
                    <td key={ver} className="py-2.5 px-2 text-center text-xs text-muted/25">
                      —
                    </td>
                  );
                }
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

      {/* Missing model footnote */}
      {missingModels.length > 0 && (
        <p className="mt-3 text-[10px] leading-snug text-muted/40">
          — = not yet run (e.g. lineup not confirmed → v4 unavailable, falls back implicitly to v3)
        </p>
      )}
    </div>
  );
}
