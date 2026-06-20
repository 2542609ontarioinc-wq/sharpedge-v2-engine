import type { MLBPlayerProp } from "@/lib/types";
import { formatFirstPitch, formatPercent, formatSignedPercent } from "@/lib/format";
import { Badge, confidenceTierVariant } from "./Badge";
import { TeamLogo } from "./TeamLogo";
import { PlayerAvatar } from "./PlayerAvatar";
import { LiveScoreModule } from "./LiveScoreModule";
import type { LiveScore } from "@/hooks/useLiveScores";

const PROP_LABELS: Record<string, string> = {
  strikeouts: "Strikeouts",
  outs_recorded: "Outs Recorded",
  earned_runs: "Earned Runs",
  hits_allowed: "Hits Allowed",
  walks: "Walks",
  h_r_rbi: "H+R+RBI",
};

function formatOddsAmerican(am: number | null, dec: number | null): string | null {
  if (am !== null) return `${am > 0 ? "+" : ""}${am}`;
  if (dec !== null) return dec.toFixed(2);
  return null;
}

function edgeFlagVariant(flag: string | null): "elite" | "muted" | "watch" {
  if (flag === "REAL") return "elite";
  if (flag === "suspect") return "watch";
  return "muted";
}

function PropRow({ prop }: { prop: MLBPlayerProp }) {
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

  return (
    <div
      className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm ${
        isBOD
          ? "border-watch/30 bg-watch/5"
          : isNoisier
            ? "border-border/50 opacity-80"
            : "border-border"
      }`}
    >
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
  );
}

export function MLBPlayerPropsCard({
  gameId,
  props,
  liveState,
}: {
  gameId: string;
  props: MLBPlayerProp[];
  liveState?: Map<string, LiveScore>;
}) {
  if (props.length === 0) return null;

  const first = props[0];
  const live = liveState?.get(gameId);
  const isLive = live?.isLive ?? false;

  const pitcherProps = props.filter((p) => p.playerType === "pitcher");
  const batterProps = props.filter((p) => p.playerType === "batter");

  // Group pitcher props by player name — keep playerMlbId per player
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
    "strikeouts",
    "outs_recorded",
    "earned_runs",
    "hits_allowed",
    "walks",
    "h_r_rbi",
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

      {/* Live score (if live) — shown at top of card */}
      {live && props[0] && (
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
        {/* Pitcher sections with avatar */}
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
                <PropRow key={p.propMarket} prop={p} />
              ))}
            </div>
          </div>
        ))}

        {/* Batter sections with avatar */}
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
                      <PropRow key={`${p.playerName}-${p.propMarket}`} prop={p} />
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
