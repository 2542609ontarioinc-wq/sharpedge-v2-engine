import type { MLBPlayerProp } from "@/lib/types";
import { formatFirstPitch, formatPercent, formatSignedPercent } from "@/lib/format";
import { Badge, confidenceTierVariant } from "./Badge";
import { TeamLogo } from "./TeamLogo";
import { PlayerAvatar } from "./PlayerAvatar";
import { LiveScoreModule } from "./LiveScoreModule";
import type { LiveScore } from "@/hooks/useLiveScores";
import type { LivePlayerStat, LivePlayerStatsMap } from "@/hooks/useLivePlayerStats";

// ─── Prop market labels ───────────────────────────────────────────────────────

const PROP_LABELS: Record<string, string> = {
  strikeouts:    "Strikeouts",
  outs_recorded: "Outs Recorded",
  earned_runs:   "Earned Runs",
  hits_allowed:  "Hits Allowed",
  walks:         "Walks",
  h_r_rbi:       "H+R+RBI",
};

// ─── Live prop status ────────────────────────────────────────────────────────

type LivePropStatus =
  | "currently_winning"
  | "currently_losing"
  | "too_close"
  | "on_track"    // Under pick: player is under the line but game isn't over
  | null;

function getStatValue(market: string, stat: LivePlayerStat): number | null {
  switch (market) {
    case "h_r_rbi":       return stat.hits + stat.runs + stat.rbi;
    case "strikeouts":    return stat.strikeOuts;
    case "outs_recorded": return stat.outs;
    case "earned_runs":   return stat.earnedRuns;
    case "hits_allowed":  return stat.hitsAllowed;
    case "walks":         return stat.walks;
    default:              return null;
  }
}

function computeLivePropStatus(
  market: string,
  side: "Over" | "Under" | null,
  line: number | null,
  stat: LivePlayerStat,
): LivePropStatus {
  if (!side || line === null) return null;
  const current = getStatValue(market, stat);
  if (current === null) return null;

  if (side === "Over") {
    if (current > line)  return "currently_winning";
    if (current === line) return "too_close";
    return "currently_losing";
  } else {
    // Under — crossing the line is already a loss; being under is provisional
    if (current > line)  return "currently_losing";
    if (current === line) return "too_close";
    return "on_track";   // not "winning" — game isn't over
  }
}

function formatLiveStatDisplay(market: string, stat: LivePlayerStat): string {
  switch (market) {
    case "h_r_rbi": {
      const total = stat.hits + stat.runs + stat.rbi;
      return `${total} so far (${stat.hits}H / ${stat.runs}R / ${stat.rbi}RBI)`;
    }
    case "strikeouts":    return `${stat.strikeOuts} K so far`;
    case "outs_recorded": return `${stat.outs} outs recorded`;
    case "earned_runs":   return `${stat.earnedRuns} ER so far`;
    case "hits_allowed":  return `${stat.hitsAllowed} H allowed`;
    case "walks":         return `${stat.walks} BB so far`;
    default:              return "";
  }
}

const STATUS_CHIP: Record<NonNullable<LivePropStatus>, string> = {
  currently_winning: "bg-elite/15 text-elite border border-elite/30",
  currently_losing:  "bg-reject/15 text-reject border border-reject/30",
  too_close:         "bg-watch/15 text-watch border border-watch/30",
  on_track:          "bg-muted/10 text-muted border border-border-strong",
};

const STATUS_LABEL: Record<NonNullable<LivePropStatus>, string> = {
  currently_winning: "Winning",
  currently_losing:  "Losing",
  too_close:         "On the line",
  on_track:          "On track (under)",
};

// ─── Odds formatter ───────────────────────────────────────────────────────────

function formatOddsAmerican(am: number | null, dec: number | null): string | null {
  if (am !== null) return `${am > 0 ? "+" : ""}${am}`;
  if (dec !== null) return dec.toFixed(2);
  return null;
}

function edgeFlagVariant(flag: string | null): "elite" | "muted" | "watch" {
  if (flag === "REAL")    return "elite";
  if (flag === "suspect") return "watch";
  return "muted";
}

// ─── PropRow ──────────────────────────────────────────────────────────────────

function PropRow({
  prop,
  gameId,
  livePlayerStats,
  isLive,
}: {
  prop: MLBPlayerProp;
  gameId: string;
  livePlayerStats?: LivePlayerStatsMap;
  isLive: boolean;
}) {
  const label = PROP_LABELS[prop.propMarket] ?? prop.propMarket;
  const oddsStr = formatOddsAmerican(prop.bestOddsAmerican, prop.bestOddsDecimal);
  const isNoisier = prop.confidenceNote === "noisier";
  const isBOD = prop.confidenceTier === "Bet of the Day";

  const calProb =
    prop.pickSide === "Over"
      ? prop.calibratedOverProb
      : prop.calibratedOverProb !== null
        ? 100 - prop.calibratedOverProb
        : null;

  // Live player stat lookup
  const liveStat =
    isLive && prop.playerMlbId
      ? (livePlayerStats?.get(`${gameId}:${prop.playerMlbId}`) ?? null)
      : null;

  const livePropStatus = liveStat
    ? computeLivePropStatus(prop.propMarket, prop.pickSide, prop.marketLine, liveStat)
    : null;

  const liveStatDisplay = liveStat ? formatLiveStatDisplay(prop.propMarket, liveStat) : null;

  return (
    <div
      className={`flex flex-col gap-1.5 rounded-lg border px-3 py-2 text-sm ${
        isBOD
          ? "border-watch/30 bg-watch/5"
          : isNoisier
            ? "border-border/50 opacity-80"
            : "border-border"
      }`}
    >
      {/* Main pick line */}
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="font-medium text-ink truncate">{prop.playerName}</span>
            {isNoisier && (
              <span className="shrink-0 rounded px-1 py-0.5 text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20">
                noisier
              </span>
            )}
          </div>
          <div className="mt-0.5 text-xs text-muted">
            {label} {prop.pickSide}{" "}
            <span className="font-semibold text-ink">{prop.marketLine}</span>
            {prop.modelProjection !== null && (
              <span className="ml-1.5 opacity-60">
                (model: {prop.modelProjection.toFixed(1)})
              </span>
            )}
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {calProb !== null && (
            <span className="text-xs font-semibold text-ink">{formatPercent(calProb)}</span>
          )}
          {oddsStr && (
            <span className="text-xs text-muted">{oddsStr}</span>
          )}
          <Badge variant={edgeFlagVariant(prop.edgeFlag)}>
            {prop.edgeFlag === "REAL" && prop.modelEdge !== null
              ? formatSignedPercent(prop.pickSide === "Over" ? prop.modelEdge : -prop.modelEdge)
              : prop.edgeFlag ?? "—"}
          </Badge>
        </div>
      </div>

      {/* Live stat row — only when game is live and we have player stats */}
      {isLive && liveStatDisplay && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded border border-watch/20 bg-watch/5 px-2 py-1">
          <span className="size-1.5 shrink-0 rounded-full bg-watch animate-pulse" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-watch">
            Live
          </span>
          <span className="text-[10px] text-muted">{liveStatDisplay}</span>
          {livePropStatus && (
            <span
              className={`rounded-full px-1.5 py-0.5 text-[9px] font-semibold ${STATUS_CHIP[livePropStatus]}`}
            >
              {STATUS_LABEL[livePropStatus]}
            </span>
          )}
          <span className="ml-auto text-[9px] uppercase tracking-wide text-muted/40">
            not final
          </span>
        </div>
      )}
    </div>
  );
}

// ─── Main card ────────────────────────────────────────────────────────────────

export function MLBPlayerPropsCard({
  gameId,
  props,
  liveState,
  livePlayerStats,
}: {
  gameId: string;
  props: MLBPlayerProp[];
  liveState?: Map<string, LiveScore>;
  livePlayerStats?: LivePlayerStatsMap;
}) {
  if (props.length === 0) return null;

  const first = props[0];
  const live = liveState?.get(gameId);
  const isLive = live?.isLive ?? false;

  const pitcherProps = props.filter((p) => p.playerType === "pitcher");
  const batterProps  = props.filter((p) => p.playerType === "batter");

  // Group pitcher props by player name, keeping playerMlbId
  const pitcherMap = new Map<string, { props: MLBPlayerProp[]; playerMlbId: number | null }>();
  for (const p of pitcherProps) {
    const existing = pitcherMap.get(p.playerName) ?? { props: [], playerMlbId: p.playerMlbId };
    existing.props.push(p);
    if (!existing.playerMlbId && p.playerMlbId) existing.playerMlbId = p.playerMlbId;
    pitcherMap.set(p.playerName, existing);
  }

  // Batter playerMlbId by player name
  const batterMlbIds = new Map<string, number | null>();
  for (const p of batterProps) {
    if (!batterMlbIds.has(p.playerName)) batterMlbIds.set(p.playerName, p.playerMlbId);
  }

  const MARKET_ORDER = [
    "strikeouts", "outs_recorded", "earned_runs", "hits_allowed", "walks", "h_r_rbi",
  ];
  const sortProps = (ps: MLBPlayerProp[]) =>
    [...ps].sort(
      (a, b) => MARKET_ORDER.indexOf(a.propMarket) - MARKET_ORDER.indexOf(b.propMarket)
    );

  // Group batter props by player name
  const batterMap = new Map<string, MLBPlayerProp[]>();
  for (const p of batterProps) {
    const list = batterMap.get(p.playerName) ?? [];
    list.push(p);
    batterMap.set(p.playerName, list);
  }

  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-1.5 flex-wrap">
            <TeamLogo team={first.awayTeam} size={20} />
            <span className="text-sm font-medium text-ink">{first.awayTeam}</span>
            <span className="text-muted text-xs">@</span>
            <TeamLogo team={first.homeTeam} size={20} />
            <span className="text-sm font-medium text-ink">{first.homeTeam}</span>
          </div>
          <div className="mt-0.5 flex items-center gap-2">
            <p className="text-xs text-muted">{formatFirstPitch(first.gameTime)}</p>
            {isLive && (
              <span className="flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-watch animate-pulse" />
                <span className="text-[10px] font-bold text-watch uppercase tracking-wide">Live</span>
              </span>
            )}
          </div>
        </div>
        <span className="shrink-0 rounded-full border border-border-strong/40 bg-bg-2 px-2 py-0.5 text-[10px] text-muted">
          ⚾ Player Props
        </span>
      </div>

      {/* Game-level live score (if live) */}
      {live && (
        <div className="mb-3">
          <LiveScoreModule
            live={live}
            market={props[0].propMarket}
            pick={`${props[0].pickSide} ${props[0].marketLine}`}
            homeTeam={first.homeTeam}
            awayTeam={first.awayTeam}
          />
        </div>
      )}

      <div className="flex flex-col gap-3">
        {/* Pitcher sections */}
        {[...pitcherMap.entries()].map(([name, { props: ps, playerMlbId }]) => (
          <div key={name}>
            <div className="mb-1.5 flex items-center gap-2">
              <PlayerAvatar playerMlbId={playerMlbId} playerName={name} size={28} />
              <p className="text-xs font-semibold text-muted uppercase tracking-wide">
                {name} · {ps[0].teamName ?? (ps[0].side === "home" ? first.homeTeam : first.awayTeam)}
              </p>
            </div>
            <div className="flex flex-col gap-1">
              {sortProps(ps).map((p) => (
                <PropRow
                  key={p.propMarket}
                  prop={p}
                  gameId={gameId}
                  livePlayerStats={livePlayerStats}
                  isLive={isLive}
                />
              ))}
            </div>
          </div>
        ))}

        {/* Batter sections */}
        {batterMap.size > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-semibold text-muted uppercase tracking-wide">
              Batters
            </p>
            <div className="flex flex-col gap-2">
              {[...batterMap.entries()].map(([name, ps]) => (
                <div key={name}>
                  <div className="mb-1 flex items-center gap-2">
                    <PlayerAvatar
                      playerMlbId={batterMlbIds.get(name) ?? null}
                      playerName={name}
                      size={24}
                    />
                    <span className="text-[11px] font-medium text-muted">{name}</span>
                  </div>
                  <div className="flex flex-col gap-1">
                    {sortProps(ps).map((p) => (
                      <PropRow
                        key={`${p.playerName}-${p.propMarket}`}
                        prop={p}
                        gameId={gameId}
                        livePlayerStats={livePlayerStats}
                        isLive={isLive}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <p className="mt-3 text-[10px] leading-snug text-muted/50">
        Internal — 30% model / 70% market calibration. Noisier markets (ER, H, BB) have high per-start variance.
      </p>
    </div>
  );
}
