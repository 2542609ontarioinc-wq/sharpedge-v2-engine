"use client";

import { useEffect, useRef, useState } from "react";
import type { LiveScore } from "./useLiveScores";

export type LivePlayerStat = {
  // Batting
  hits: number;
  runs: number;
  rbi: number;
  // Pitching
  strikeOuts: number;
  outs: number;        // total outs recorded (inningsPitched converted: "4.2" → 14)
  hitsAllowed: number;
  walks: number;
  earnedRuns: number;
};

// Map key: "${gameId}:${playerMlbId}"
export type LivePlayerStatsMap = Map<string, LivePlayerStat>;

const POLL_MS = 45_000;

function parseOuts(ip: string | undefined | null): number {
  if (!ip) return 0;
  const [whole, partial] = ip.split(".").map(Number);
  return (whole ?? 0) * 3 + (partial ?? 0);
}

async function fetchBoxscore(gameId: string, gamePk: number): Promise<LivePlayerStatsMap> {
  const result: LivePlayerStatsMap = new Map();
  try {
    const url = `https://statsapi.mlb.com/api/v1/game/${gamePk}/boxscore`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return result;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data: any = await res.json();

    for (const side of ["home", "away"] as const) {
      const players = data?.teams?.[side]?.players ?? {};
      for (const playerData of Object.values(players)) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const p = playerData as any;
        const pid: number | undefined = p?.person?.id;
        if (!pid) continue;
        const batting = p?.stats?.batting ?? {};
        const pitching = p?.stats?.pitching ?? {};
        result.set(`${gameId}:${pid}`, {
          hits:        batting.hits        ?? 0,
          runs:        batting.runs        ?? 0,
          rbi:         batting.rbi         ?? 0,
          strikeOuts:  pitching.strikeOuts  ?? 0,
          outs:        parseOuts(pitching.inningsPitched),
          hitsAllowed: pitching.hits        ?? 0,
          walks:       pitching.baseOnBalls ?? 0,
          earnedRuns:  pitching.earnedRuns  ?? 0,
        });
      }
    }
  } catch (e) {
    console.error(`[useLivePlayerStats] boxscore error gamePk=${gamePk}`, e);
  }
  return result;
}

/**
 * Polls MLB Stats API boxscore endpoints for per-player live stats.
 * Only fetches when at least one game in liveState is live + has a gamePk.
 * Cleans up interval when no live games remain or on unmount.
 * Never writes to any table.
 */
export function useLivePlayerStats(liveState: Map<string, LiveScore>): LivePlayerStatsMap {
  const [stats, setStats] = useState<LivePlayerStatsMap>(new Map());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Keep a stable ref so the interval callback always sees the latest liveState
  const liveStateRef = useRef(liveState);
  liveStateRef.current = liveState;

  // Derive a stable string key representing which gamePks are currently live.
  // When this changes, the effect re-runs so we start fetching newly-live games.
  const liveGamePksKey = [...liveState.entries()]
    .filter(([, s]) => s.isLive && s.gamePk !== null)
    .map(([, s]) => s.gamePk)
    .sort()
    .join(",");

  useEffect(() => {
    async function fetchAllStats() {
      const current = liveStateRef.current;
      const liveGames = [...current.entries()].filter(
        ([, s]) => s.isLive && s.gamePk !== null
      );

      if (liveGames.length === 0) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        return;
      }

      const combined: LivePlayerStatsMap = new Map();
      await Promise.all(
        liveGames.map(async ([gameId, score]) => {
          if (score.gamePk === null) return;
          const partial = await fetchBoxscore(gameId, score.gamePk);
          for (const [k, v] of partial) combined.set(k, v);
        })
      );
      setStats(combined);

      // Start interval once we have live games (idempotent check)
      if (!intervalRef.current) {
        intervalRef.current = setInterval(fetchAllStats, POLL_MS);
      }
    }

    fetchAllStats();

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  // liveGamePksKey is the trigger: re-run when the set of live games changes
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveGamePksKey]);

  return stats;
}
