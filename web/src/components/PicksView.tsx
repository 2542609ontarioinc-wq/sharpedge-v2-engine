"use client";

import { useState } from "react";
import type { SafeZonePick, SharpPick, TrackRecord } from "@/lib/types";
import { SharpPickCard } from "./SharpPickCard";
import { SafeZoneCard } from "./SafeZoneCard";
import { TrackRecordView } from "./TrackRecordView";
import { EmptyState } from "./EmptyState";

type Tab = "sharp" | "safe" | "record";

export function PicksView({
  sharpPicks,
  safeZone,
  trackRecord,
}: {
  sharpPicks: SharpPick[];
  safeZone: SafeZonePick[];
  trackRecord: TrackRecord;
}) {
  const [tab, setTab] = useState<Tab>("sharp");

  return (
    <div>
      <div className="mb-6 inline-flex rounded-full border border-border bg-surface p-1">
        <TabButton active={tab === "sharp"} onClick={() => setTab("sharp")}>
          Sharp Picks
          <span className="ml-1.5 text-xs opacity-70">{sharpPicks.length}</span>
        </TabButton>
        <TabButton active={tab === "safe"} onClick={() => setTab("safe")}>
          Safe Zone
          <span className="ml-1.5 text-xs opacity-70">{safeZone.length}</span>
        </TabButton>
        <TabButton active={tab === "record"} onClick={() => setTab("record")}>
          Track Record
        </TabButton>
      </div>

      {tab === "sharp" ? (
        sharpPicks.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {sharpPicks.map((pick) => (
              <SharpPickCard key={`${pick.gameId}-${pick.market}`} pick={pick} />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No sharp picks right now"
            subtitle="The engine hasn't cleared any picks for value + safety yet. Check back closer to kickoff."
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
      )}
    </div>
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
