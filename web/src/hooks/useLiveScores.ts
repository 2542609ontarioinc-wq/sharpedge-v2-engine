"use client";

import { useEffect, useRef, useState } from "react";

export type GameInfo = {
  gameId: string;
  homeTeam: string;
  awayTeam: string;
  gameTime: string | null;
};

export type LiveScore = {
  homeScore: number;
  awayScore: number;
  inning: number | null;
  inningHalf: string | null;
  outs: number | null;
  isLive: boolean;
  gameStatus: string;
};

const MLB_SCHEDULE = "https://statsapi.mlb.com/api/v1/schedule";
const POLL_MS = 45_000;

function torontoDate(iso: string): string {
  const d = new Date(iso);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto" }).format(d);
}

function todayToronto(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto" }).format(new Date());
}

function norm(s: string): string {
  return s.toLowerCase().trim();
}

function teamsMatch(a: string, b: string): boolean {
  const na = norm(a), nb = norm(b);
  if (na === nb) return true;
  const la = na.split(/\s+/).at(-1) ?? "";
  const lb = nb.split(/\s+/).at(-1) ?? "";
  return la.length > 2 && la === lb;
}

async function fetchDateScores(
  date: string,
  lookup: Map<string, string>
): Promise<Map<string, LiveScore>> {
  const result = new Map<string, LiveScore>();
  const url = `${MLB_SCHEDULE}?sportId=1&date=${date}&hydrate=linescore`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) return result;
  const data = await res.json();

  for (const dateBlock of data?.dates ?? []) {
    for (const g of dateBlock?.games ?? []) {
      const mlbDate: string = g.officialDate ?? g.gameDate?.slice(0, 10) ?? "";
      const mlbHome: string = g.teams?.home?.team?.name ?? "";
      const mlbAway: string = g.teams?.away?.team?.name ?? "";

      let gameId: string | null = null;
      // Try exact date+team match first
      const exactKey = `${mlbDate}|${norm(mlbHome)}|${norm(mlbAway)}`;
      if (lookup.has(exactKey)) {
        gameId = lookup.get(exactKey)!;
      } else {
        // Try nickname-fallback by scanning all lookup keys for this date
        for (const [key, gid] of lookup) {
          const parts = key.split("|");
          if (parts[0] !== mlbDate) continue;
          if (teamsMatch(mlbHome, parts[1]) && teamsMatch(mlbAway, parts[2])) {
            gameId = gid;
            break;
          }
        }
      }
      if (!gameId) continue;

      const ls = g.linescore ?? {};
      const lsTeams = ls.teams ?? {};
      const detailedState: string = g.status?.detailedState ?? "";
      const isLive =
        detailedState.toLowerCase().includes("live") ||
        detailedState.toLowerCase().includes("in progress");

      result.set(gameId, {
        homeScore: lsTeams.home?.runs ?? 0,
        awayScore: lsTeams.away?.runs ?? 0,
        inning: ls.currentInning ?? null,
        inningHalf: ls.inningHalf ?? null,
        outs: ls.outs ?? null,
        isLive,
        gameStatus: detailedState,
      });
    }
  }
  return result;
}

export function useLiveScores(games: GameInfo[]): Map<string, LiveScore> {
  const [scores, setScores] = useState<Map<string, LiveScore>>(new Map());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Stable ref so fetchScores closure always sees fresh games list
  const gamesRef = useRef<GameInfo[]>(games);
  gamesRef.current = games;

  useEffect(() => {
    async function fetchScores() {
      const currentGames = gamesRef.current;
      if (currentGames.length === 0) return;

      // Build lookup map: "date|homeNorm|awayNorm" → gameId
      const lookup = new Map<string, string>();
      const dates = new Set<string>();
      dates.add(todayToronto());

      for (const g of currentGames) {
        if (g.gameTime) {
          try {
            const d = torontoDate(g.gameTime);
            dates.add(d);
            lookup.set(`${d}|${norm(g.homeTeam)}|${norm(g.awayTeam)}`, g.gameId);
          } catch {
            // invalid date, skip
          }
        }
      }

      const combined = new Map<string, LiveScore>();
      await Promise.all(
        [...dates].map(async (date) => {
          try {
            const partial = await fetchDateScores(date, lookup);
            for (const [gid, score] of partial) combined.set(gid, score);
          } catch (e) {
            console.error("[useLiveScores] fetch error for", date, e);
          }
        })
      );

      setScores(combined);

      // Manage polling: only run while at least one game is live
      const anyLive = [...combined.values()].some((s) => s.isLive);
      if (anyLive && !intervalRef.current) {
        intervalRef.current = setInterval(fetchScores, POLL_MS);
      } else if (!anyLive && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    fetchScores();

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentionally empty — gamesRef keeps it fresh

  return scores;
}
