import type { MLBSafeZonePick } from "@/lib/types";
import { formatFirstPitch, formatPercent } from "@/lib/format";
import { Badge } from "./Badge";
import { ProbabilityBar } from "./ProbabilityBar";
import { TeamLogo } from "./TeamLogo";
import { LiveScoreModule } from "./LiveScoreModule";
import type { LiveScore } from "@/hooks/useLiveScores";

const MARKET_LABELS: Record<string, string> = {
  moneyline: "Moneyline",
  totals: "Totals",
  run_line: "Run Line",
};

export function MLBSafeZoneCard({
  pick,
  liveState,
}: {
  pick: MLBSafeZonePick;
  liveState?: Map<string, LiveScore>;
}) {
  const live = liveState?.get(pick.gameId);
  const isLive = live?.isLive ?? false;

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-surface p-5 backdrop-blur transition-colors hover:border-border-strong">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          {/* Team row with logos */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <TeamLogo team={pick.awayTeam} size={20} />
            <span className="text-sm font-medium text-ink">{pick.awayTeam}</span>
            <span className="text-muted text-xs">@</span>
            <TeamLogo team={pick.homeTeam} size={20} />
            <span className="text-sm font-medium text-ink">{pick.homeTeam}</span>
          </div>
          <div className="mt-1 flex items-center gap-2">
            <p className="text-xs text-muted">{formatFirstPitch(pick.gameTime)}</p>
            {isLive && (
              <span className="flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-watch animate-pulse" />
                <span className="text-[10px] font-bold text-watch uppercase tracking-wide">Live</span>
              </span>
            )}
          </div>
          {pick.sharpPick && (
            <p className="mt-1 text-xs text-muted/70">
              Sharp pick:{" "}
              <span className="font-medium text-muted">{pick.sharpPick}</span>
              {pick.sharpMarket && (
                <span className="ml-1 text-muted/50">
                  ({MARKET_LABELS[pick.sharpMarket] ?? pick.sharpMarket})
                </span>
              )}
            </p>
          )}
        </div>
        {/* MLB badge */}
        <span className="shrink-0 rounded-full border border-border-strong/40 bg-bg-2 px-2 py-0.5 text-[10px] text-muted">
          ⚾ MLB
        </span>
      </div>

      {/* Balanced pick */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-muted">
          <span>Balanced pick</span>
          <span className="font-semibold text-ink">{formatPercent(pick.balancedProb)} win</span>
        </div>
        <p className="text-base font-semibold text-ink">{pick.balancedPick ?? "—"}</p>
        <ProbabilityBar value={pick.balancedProb} variant="accent" />
      </div>

      {/* Banker pick */}
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
          {pick.bankerPick ?? (
            <span className="text-sm font-normal text-muted">No banker play for this game</span>
          )}
        </p>
        {pick.bankerPick && <ProbabilityBar value={pick.bankerProb} variant="elite" />}
      </div>

      {/* Live score module — shown once per card for the balanced pick */}
      {live && pick.balancedPick && (
        <LiveScoreModule
          live={live}
          market="safe_balanced"
          pick={pick.balancedPick}
          homeTeam={pick.homeTeam}
          awayTeam={pick.awayTeam}
        />
      )}
    </div>
  );
}
