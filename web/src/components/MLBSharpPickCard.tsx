import type { MLBSharpPick } from "@/lib/types";
import { formatFirstPitch, formatPercent, formatSignedPercent } from "@/lib/format";
import { Badge, confidenceTierVariant } from "./Badge";
import { ProbabilityBar } from "./ProbabilityBar";

const MARKET_LABELS: Record<string, string> = {
  moneyline: "Moneyline",
  totals: "Totals",
  run_line: "Run Line",
};

function formatOdds(decimal: number | null, american: number | null): string | null {
  if (american !== null) return `${american > 0 ? "+" : ""}${american}`;
  if (decimal !== null) return decimal.toFixed(2);
  return null;
}

export function MLBSharpPickCard({ pick }: { pick: MLBSharpPick }) {
  const oddsStr = formatOdds(pick.oddsDecimal, pick.oddsAmerican);
  const isBOD = pick.confidenceTier === "Bet of the Day";

  return (
    <div
      className={`flex flex-col gap-4 rounded-2xl border bg-surface p-5 backdrop-blur transition-colors hover:border-border-strong ${
        isBOD ? "border-watch/40" : "border-border"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <Badge variant="muted">{MARKET_LABELS[pick.market] ?? pick.market}</Badge>
        <div className="flex items-center gap-2">
          {pick.confidenceTier && (
            <Badge variant={confidenceTierVariant(pick.confidenceTier)}>
              {isBOD ? "★ " : ""}{pick.confidenceTier}
            </Badge>
          )}
          {pick.isRealValue && (
            <Badge variant="elite">{formatSignedPercent(pick.edge)} edge</Badge>
          )}
        </div>
      </div>

      <div>
        <p className="text-sm font-medium text-ink">
          {pick.awayTeam} <span className="text-muted">@</span> {pick.homeTeam}
        </p>
        <p className="mt-1 text-xs text-muted">{formatFirstPitch(pick.gameTime)}</p>
      </div>

      <div className="rounded-xl border border-border bg-bg-2/60 px-4 py-3">
        <p className="text-lg font-semibold text-ink">{pick.pick}</p>
        {oddsStr && (
          <p className="mt-0.5 text-xs text-muted">
            {oddsStr}
            {pick.bookmaker && <span className="ml-1.5">via {pick.bookmaker}</span>}
          </p>
        )}
      </div>

      <div>
        <div className="mb-1.5 flex items-center justify-between text-xs text-muted">
          <span>Calibrated confidence</span>
          <span className="font-semibold text-ink">{formatPercent(pick.calibratedConfidence)}</span>
        </div>
        <ProbabilityBar value={pick.calibratedConfidence} variant="accent" />
      </div>

      {pick.secondaryPick && (
        <p className="text-xs text-muted/70">
          Also watching:{" "}
          <span className="font-medium text-muted">{pick.secondaryPick}</span>
          {pick.secondaryMarket && (
            <span className="ml-1 text-muted/50">
              ({MARKET_LABELS[pick.secondaryMarket] ?? pick.secondaryMarket})
            </span>
          )}
        </p>
      )}

      <p className="text-[10px] leading-snug text-muted/50">
        Internal — tier is confidence-ranked, not proven to win more.
      </p>
    </div>
  );
}
