import type { SafeZonePick } from "@/lib/types";
import { formatKickoff, formatPercent } from "@/lib/format";
import { Badge } from "./Badge";
import { ProbabilityBar } from "./ProbabilityBar";

export function SafeZoneCard({ pick }: { pick: SafeZonePick }) {
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-surface p-5 backdrop-blur transition-colors hover:border-border-strong">
      <div>
        <p className="text-sm font-medium text-ink">
          {pick.homeTeam} <span className="text-muted">vs</span> {pick.awayTeam}
        </p>
        <p className="mt-1 text-xs text-muted">{formatKickoff(pick.kickoff)}</p>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted">
          <span>Balanced pick</span>
          <span className="font-semibold text-ink">{formatPercent(pick.balancedProb)} win</span>
        </div>
        <p className="text-base font-semibold text-ink">{pick.balancedPick ?? "—"}</p>
        <ProbabilityBar value={pick.balancedProb} variant="accent" />
      </div>

      <div className="space-y-2 rounded-xl border border-border bg-bg-2/60 p-3">
        <div className="flex items-center justify-between text-xs text-muted">
          <span className="flex items-center gap-2">
            Banker
            {pick.bankerPick && <Badge variant="elite">80%+</Badge>}
          </span>
          {pick.bankerPick && (
            <span className="font-semibold text-ink">{formatPercent(pick.bankerProb)} win</span>
          )}
        </div>
        <p className="text-base font-semibold text-ink">
          {pick.bankerPick ?? <span className="text-sm font-normal text-muted">No banker play for this match</span>}
        </p>
        {pick.bankerPick && <ProbabilityBar value={pick.bankerProb} variant="elite" />}
      </div>
    </div>
  );
}
