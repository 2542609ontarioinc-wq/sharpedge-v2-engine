import { computeLivePickStatus } from "@/lib/data";
import type { LiveScore } from "@/hooks/useLiveScores";

const STATUS_CHIP: Record<string, string> = {
  currently_winning: "bg-elite/15 text-elite border border-elite/30",
  currently_losing:  "bg-reject/15 text-reject border border-reject/30",
  too_close:         "bg-watch/15 text-watch border border-watch/30",
};

const STATUS_LABEL: Record<string, string> = {
  currently_winning: "Currently Winning",
  currently_losing:  "Currently Losing",
  too_close:         "Too Close",
};

function inningLabel(inning: number | null, half: string | null): string {
  if (inning === null) return "";
  const arrow = half === "Top" ? "▲" : half === "Bottom" ? "▼" : "";
  return `${arrow} ${inning}`.trim();
}

export function LiveScoreModule({
  live,
  market,
  pick,
  homeTeam,
  awayTeam,
}: {
  live: LiveScore;
  market: string;
  pick: string;
  homeTeam: string;
  awayTeam: string;
}) {
  if (!live.isLive) return null;

  const status = computeLivePickStatus(market, pick, homeTeam, awayTeam, {
    gameId: "",
    homeScore: live.homeScore,
    awayScore: live.awayScore,
    inning: live.inning,
    inningHalf: live.inningHalf,
    outs: live.outs,
    gameStatus: live.gameStatus,
    homePitcher: null,
    awayPitcher: null,
    capturedAt: null,
  });

  return (
    <div className="rounded-lg border border-watch/30 bg-watch/5 px-3 py-2 mt-2">
      {/* Header row */}
      <div className="flex items-center gap-2 mb-1.5">
        <span className="size-1.5 rounded-full bg-watch animate-pulse shrink-0" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-watch">
          Live — Not Final
        </span>
      </div>

      {/* Score + inning + outs */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-sm font-bold text-ink font-mono">
          {live.awayScore} – {live.homeScore}
        </span>
        {live.inning !== null && (
          <span className="text-xs text-muted">
            {inningLabel(live.inning, live.inningHalf)}
          </span>
        )}
        {live.outs !== null && (
          <span className="text-xs text-muted/60">
            {live.outs} out{live.outs !== 1 ? "s" : ""}
          </span>
        )}
        {status && (
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${STATUS_CHIP[status]}`}>
            {STATUS_LABEL[status]}
          </span>
        )}
      </div>

      <p className="mt-1 text-[9px] text-muted/40 uppercase tracking-wide">
        Live score — non-binding display only
      </p>
    </div>
  );
}
