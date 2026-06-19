import type { SharpPick } from "@/lib/types";
import { formatKickoff, formatPercent, formatSignedPercent } from "@/lib/format";
import { Badge, confidenceTierVariant } from "./Badge";
import { ProbabilityBar } from "./ProbabilityBar";

export function SharpPickCard({ pick }: { pick: SharpPick }) {
  const isBOD = pick.confidenceTier === "Bet of the Day";

  return (
    <div
      className={`flex flex-col gap-4 rounded-2xl border bg-surface p-5 backdrop-blur transition-colors hover:border-border-strong ${
        isBOD ? "border-watch/40" : "border-border"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <Badge variant="muted">{pick.market}</Badge>
        {pick.confidenceTier && (
          <Badge variant={confidenceTierVariant(pick.confidenceTier)}>
            {isBOD ? "★ " : ""}{pick.confidenceTier}
          </Badge>
        )}
      </div>

      <div>
        <p className="text-sm font-medium text-ink">
          {pick.homeTeam} <span className="text-muted">vs</span> {pick.awayTeam}
        </p>
        <p className="mt-1 text-xs text-muted">{formatKickoff(pick.kickoff)}</p>
      </div>

      <div className="rounded-xl border border-border bg-bg-2/60 px-4 py-3">
        <p className="text-lg font-semibold text-ink">{pick.pick}</p>
        {pick.bookmaker && (
          <p className="mt-0.5 text-xs text-muted">via {pick.bookmaker}</p>
        )}
      </div>

      <div className="flex items-end justify-between gap-4">
        <div className="flex-1">
          <div className="mb-1.5 flex items-center justify-between text-xs text-muted">
            <span>Calibrated confidence</span>
            <span className="font-semibold text-ink">{formatPercent(pick.confidence)}</span>
          </div>
          <ProbabilityBar value={pick.confidence} variant="accent" />
        </div>

        {pick.isRealValue && (
          <Badge variant="elite">{formatSignedPercent(pick.edge)} edge</Badge>
        )}
      </div>

      <p className="text-[10px] leading-snug text-muted/50">
        Internal — tier is confidence-ranked, not proven to win more.
      </p>
    </div>
  );
}
