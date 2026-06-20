"use client";

import { useState } from "react";
import type { MLBDiagnostics, MLBModelAnalytics, MLBModelLabGame, MLBPlayerProp, MLBSafeZonePick, MLBSharpPick, MLBTrackRecord, SafeZonePick, SharpPick, TrackRecord } from "@/lib/types";
import { SoccerGameGroupCard, MLBGameGroupCard } from "./GameGroupCard";
import { SafeZoneCard } from "./SafeZoneCard";
import { TrackRecordView } from "./TrackRecordView";
import { MLBSafeZoneCard } from "./MLBSafeZoneCard";
import { MLBTrackRecordView } from "./MLBTrackRecordView";
import { MLBModelLabView } from "./MLBModelLabView";
import { MLBDiagnosticsView } from "./MLBDiagnosticsView";
import { MLBPlayerPropsCard } from "./MLBPlayerPropsCard";
import { MLBSubscriberView } from "./MLBSubscriberView";
import { EmptyState } from "./EmptyState";
import { DateSelector } from "./DateSelector";

// ─── Flip to false to remove the INTERNAL badge and make the tab public ─────
const SUBSCRIBER_TAB_INTERNAL = true;

type Sport = "soccer" | "mlb";
type Tab = "sharp" | "safe" | "record" | "props" | "subscriber" | "lab" | "diagnostics";
type TierFilter = "all" | "Bet of the Day" | "Elite" | "Standard";

const TIER_FILTERS: { value: TierFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "Bet of the Day", label: "★ Bet of the Day" },
  { value: "Elite", label: "Elite" },
  { value: "Standard", label: "Standard" },
];

function groupByGame<T extends { gameId: string }>(
  picks: T[],
  getTime: (p: T) => string | null
): T[][] {
  const map = new Map<string, T[]>();
  for (const pick of picks) {
    if (!map.has(pick.gameId)) map.set(pick.gameId, []);
    map.get(pick.gameId)!.push(pick);
  }
  return [...map.values()].sort((a, b) =>
    (getTime(a[0]) ?? "").localeCompare(getTime(b[0]) ?? "")
  );
}

function gameDateToronto(gameTime: string | null): string | null {
  if (!gameTime) return null;
  const d = new Date(gameTime);
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto" }).format(d);
}

export function PicksView({
  sharpPicks,
  safeZone,
  trackRecord,
  mlbSharpPicks,
  mlbSafeZone,
  mlbTrackRecord,
  mlbPlayerProps,
  mlbModelLab,
  mlbModelAnalytics,
  mlbDiagnostics,
}: {
  sharpPicks: SharpPick[];
  safeZone: SafeZonePick[];
  trackRecord: TrackRecord;
  mlbSharpPicks: MLBSharpPick[];
  mlbSafeZone: MLBSafeZonePick[];
  mlbTrackRecord: MLBTrackRecord;
  mlbPlayerProps: MLBPlayerProp[];
  mlbModelLab: MLBModelLabGame[];
  mlbModelAnalytics: MLBModelAnalytics[];
  mlbDiagnostics: MLBDiagnostics;
}) {
  const [sport, setSport] = useState<Sport>("soccer");
  const [tab, setTab] = useState<Tab>("sharp");
  const [tierFilter, setTierFilter] = useState<TierFilter>("all");
  const [mlbSharpDate, setMlbSharpDate] = useState("all");
  const [mlbSafeDate, setMlbSafeDate] = useState("all");
  const [mlbPropsDate, setMlbPropsDate] = useState("all");

  const matchesTier = (tier: string | null) =>
    tierFilter === "all" || tier === tierFilter;

  // Derive unique sorted dates from each MLB tab's full data set (unfiltered, for the selector)
  const mlbSharpDates = [...new Set(
    mlbSharpPicks.map((p) => gameDateToronto(p.gameTime)).filter(Boolean) as string[]
  )].sort();
  const mlbSafeDates = [...new Set(
    mlbSafeZone.map((p) => gameDateToronto(p.gameTime)).filter(Boolean) as string[]
  )].sort();
  const mlbPropsDates = [...new Set(
    mlbPlayerProps.map((p) => gameDateToronto(p.gameTime)).filter(Boolean) as string[]
  )].sort();

  // Apply date filters
  const filteredMlbSharpPicks =
    mlbSharpDate === "all"
      ? mlbSharpPicks
      : mlbSharpPicks.filter((p) => gameDateToronto(p.gameTime) === mlbSharpDate);
  const filteredMlbSafeZone =
    mlbSafeDate === "all"
      ? mlbSafeZone
      : mlbSafeZone.filter((p) => gameDateToronto(p.gameTime) === mlbSafeDate);
  const filteredMlbPlayerProps =
    mlbPropsDate === "all"
      ? mlbPlayerProps
      : mlbPlayerProps.filter((p) => gameDateToronto(p.gameTime) === mlbPropsDate);

  // Game groups — a game card shows if any of its picks match the tier filter
  const soccerGroups = groupByGame(sharpPicks, (p) => p.kickoff).filter((g) =>
    g.some((p) => matchesTier(p.confidenceTier))
  );
  const mlbGroups = groupByGame(filteredMlbSharpPicks, (p) => p.gameTime).filter((g) =>
    g.some((p) => matchesTier(p.confidenceTier))
  );

  // Pick counts (for tab badge)
  const sharpCount =
    sport === "soccer"
      ? sharpPicks.filter((p) => matchesTier(p.confidenceTier)).length
      : filteredMlbSharpPicks.filter((p) => matchesTier(p.confidenceTier)).length;
  const safeCount = sport === "soccer" ? safeZone.length : filteredMlbSafeZone.length;
  const propsCount = filteredMlbPlayerProps.length;

  // Group player props by game for the Props tab
  const propsByGame = filteredMlbPlayerProps.reduce<Map<string, MLBPlayerProp[]>>((acc, p) => {
    const list = acc.get(p.gameId) ?? [];
    list.push(p);
    acc.set(p.gameId, list);
    return acc;
  }, new Map());

  const showTierFilter = tab === "sharp";

  return (
    <div>
      {/* Sport toggle */}
      <div className="mb-5 inline-flex rounded-full border border-border-strong bg-bg-2 p-1">
        <SportButton
          active={sport === "soccer"}
          onClick={() => {
            setSport("soccer");
            setTab("sharp");
            setTierFilter("all");
          }}
        >
          ⚽ Soccer
        </SportButton>
        <SportButton
          active={sport === "mlb"}
          onClick={() => {
            setSport("mlb");
            setTab("sharp");
            setTierFilter("all");
          }}
        >
          ⚾ MLB
        </SportButton>
      </div>

      {/* Tab selector */}
      <div className="mb-4 inline-flex rounded-full border border-border bg-surface p-1">
        <TabButton active={tab === "sharp"} onClick={() => setTab("sharp")}>
          Sharp Picks
          <span className="ml-1.5 text-xs opacity-70">{sharpCount}</span>
        </TabButton>
        <TabButton active={tab === "safe"} onClick={() => setTab("safe")}>
          Safe Zone
          <span className="ml-1.5 text-xs opacity-70">{safeCount}</span>
        </TabButton>
        {sport === "mlb" && (
          <TabButton active={tab === "props"} onClick={() => setTab("props")}>
            Player Props
            <span className="ml-1.5 text-xs opacity-70">{propsCount}</span>
          </TabButton>
        )}
        {sport === "mlb" && (
          <TabButton active={tab === "subscriber"} onClick={() => setTab("subscriber")}>
            Subscriber
            {SUBSCRIBER_TAB_INTERNAL && (
              <span className="ml-1.5 rounded-sm bg-watch/20 px-1 py-px text-[9px] font-bold text-watch">
                INTERNAL
              </span>
            )}
          </TabButton>
        )}
        {sport === "mlb" && (
          <TabButton active={tab === "lab"} onClick={() => setTab("lab")}>
            Model Lab
            <span className="ml-1.5 rounded-sm bg-watch/20 px-1 py-px text-[9px] font-bold text-watch">
              INTERNAL
            </span>
          </TabButton>
        )}
        {sport === "mlb" && (
          <TabButton active={tab === "diagnostics"} onClick={() => setTab("diagnostics")}>
            Diagnostics
            <span className="ml-1.5 rounded-sm bg-watch/20 px-1 py-px text-[9px] font-bold text-watch">
              INTERNAL
            </span>
          </TabButton>
        )}
        <TabButton active={tab === "record"} onClick={() => setTab("record")}>
          Track Record
        </TabButton>
      </div>

      {/* Tier filter — only on Sharp Picks tab */}
      {showTierFilter && (
        <div className="mb-6 flex flex-wrap items-center gap-2">
          {TIER_FILTERS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => setTierFilter(value)}
              className={`rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
                tierFilter === value
                  ? value === "Bet of the Day"
                    ? "border-watch/50 bg-watch/20 text-watch"
                    : value === "Elite"
                    ? "border-elite/30 bg-elite/15 text-elite"
                    : "border-border-strong bg-white/10 text-ink"
                  : "border-border text-muted hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {sport === "soccer" ? (
        tab === "sharp" ? (
          soccerGroups.length > 0 ? (
            <div className="flex flex-col gap-3">
              {soccerGroups.map((group) => (
                <SoccerGameGroupCard key={group[0].gameId} picks={group} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No sharp picks right now"
              subtitle={
                tierFilter !== "all"
                  ? `No ${tierFilter} picks today. Try a different tier filter.`
                  : "The engine hasn't cleared any picks for value + safety yet. Check back closer to kickoff."
              }
            />
          )
        ) : tab === "safe" ? (
          safeZone.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {safeZone.map((pick) => (
                <SafeZoneCard key={pick.gameId} pick={pick} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No safe zone coverage yet"
              subtitle="Balanced and banker picks for today's slate will show up here once the engine builds them."
            />
          )
        ) : (
          <TrackRecordView trackRecord={trackRecord} />
        )
      ) : tab === "sharp" ? (
        <>
          <DateSelector dates={mlbSharpDates} selected={mlbSharpDate} onChange={setMlbSharpDate} />
          {mlbGroups.length > 0 ? (
            <div className="flex flex-col gap-3">
              {mlbGroups.map((group) => (
                <MLBGameGroupCard key={group[0].gameId} picks={group} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No MLB picks today"
              subtitle={
                tierFilter !== "all"
                  ? `No ${tierFilter} picks today. Try a different tier filter.`
                  : mlbSharpDate !== "all"
                  ? "No picks on the selected date. Try a different date or select 'All dates'."
                  : "The Poisson model hasn't found a value edge on today's slate yet. Check back after first pitches approach."
              }
            />
          )}
        </>
      ) : tab === "safe" ? (
        <>
          <DateSelector dates={mlbSafeDates} selected={mlbSafeDate} onChange={setMlbSafeDate} />
          {filteredMlbSafeZone.length > 0 ? (
            <div className="grid gap-4 sm:grid-cols-2">
              {filteredMlbSafeZone.map((pick) => (
                <MLBSafeZoneCard key={pick.gameId} pick={pick} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No MLB safe zone coverage yet"
              subtitle={
                mlbSafeDate !== "all"
                  ? "No coverage on the selected date. Try a different date or select 'All dates'."
                  : "Balanced and banker run-line/total plays for today's games will appear here once the engine runs."
              }
            />
          )}
        </>
      ) : tab === "props" ? (
        <>
          <DateSelector dates={mlbPropsDates} selected={mlbPropsDate} onChange={setMlbPropsDate} />
          {propsByGame.size > 0 ? (
            <div className="flex flex-col gap-3">
              {[...propsByGame.entries()].map(([gameId, props]) => (
                <MLBPlayerPropsCard key={gameId} gameId={gameId} props={props} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="No player props yet"
              subtitle={
                mlbPropsDate !== "all"
                  ? "No props on the selected date. Try a different date or select 'All dates'."
                  : "Pitcher K/Outs, ER, H, BB and batter H+R+RBI props will appear here once the engine runs and market odds are available."
              }
            />
          )}
        </>
      ) : tab === "subscriber" ? (
        <MLBSubscriberView
          sharpPicks={mlbSharpPicks}
          safeZone={mlbSafeZone}
          playerProps={mlbPlayerProps}
        />
      ) : tab === "lab" ? (
        <MLBModelLabView games={mlbModelLab} analytics={mlbModelAnalytics} />
      ) : tab === "diagnostics" ? (
        <MLBDiagnosticsView data={mlbDiagnostics} />
      ) : (
        <MLBTrackRecordView trackRecord={mlbTrackRecord} />
      )}
    </div>
  );
}

function SportButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-5 py-2 text-sm font-bold transition-colors ${
        active ? "bg-accent text-bg" : "text-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
        active ? "bg-accent text-bg" : "text-muted hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
