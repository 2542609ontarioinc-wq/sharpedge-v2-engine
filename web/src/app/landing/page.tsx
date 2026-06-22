// ─── INTERNAL GATE ──────────────────────────────────────────────────────────
// Flip LANDING_PAGE_ENABLED to `true` when ready for the public.
// While false, an "INTERNAL PREVIEW" ribbon renders at the top.
// Mirror of SUBSCRIBER_TAB_INTERNAL in PicksView.tsx.
const LANDING_PAGE_ENABLED = false;

// Flip ADMIN_PREVIEW to `true` (or append ?admin=1 to the URL) to show the
// full subscriber experience below the landing page.
// VISUAL DEV ONLY — no Supabase session, no subscription check.
// Replace with Supabase Auth + subscription middleware before launch.
const ADMIN_PREVIEW = false;
// ────────────────────────────────────────────────────────────────────────────

import {
  getMLBSharpPicks,
  getMLBSafeZone,
  getMLBPlayerProps,
  getMLBDiagnostics,
} from "@/lib/data";
import { LandingPage } from "@/components/LandingPage";
import type { MLBPickDetail, MLBPlayerProp, MLBSafeZonePick, MLBSharpPick } from "@/lib/types";
import type { GameInfo } from "@/hooks/useLiveScores";

export const revalidate = 60;

// ─── Shared types (imported by LandingPage.tsx via `import type`) ────────────

export type FeaturedPick = {
  awayTeam: string;
  homeTeam: string;
  pick: string;
  market: string;
  confidence: number | null;
  gameTime: string | null;
  source: "sharp" | "safe";
  /** Undefined = today's pick. Set to e.g. "Next pick — Tue Jun 24" for future dates. */
  dateLabel?: string;
};

export type AdminPreviewData = {
  sharpPicks: MLBSharpPick[];
  safeZone: MLBSafeZonePick[];
  playerProps: MLBPlayerProp[];
  gradedPicks: MLBPickDetail[];
  allGames: GameInfo[];
};

// ─── Date helpers (server-side, Toronto timezone) ─────────────────────────────

function todayTorontoISO(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto" }).format(new Date());
}

function torontoGameDate(gameTime: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Toronto" }).format(
    new Date(gameTime)
  );
}

function futureDateLabel(gameTime: string | null): string | undefined {
  if (!gameTime) return undefined;
  const d = new Date(gameTime);
  if (isNaN(d.getTime())) return undefined;
  return (
    "Next pick — " +
    new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Toronto",
      weekday: "short",
      month: "short",
      day: "numeric",
    }).format(d)
  );
}

// ─── Pick selection: today first, then next upcoming labeled ─────────────────

function selectFeaturedPick(
  sharpPicks: MLBSharpPick[],
  safeZone: MLBSafeZonePick[]
): FeaturedPick | null {
  const today = todayTorontoISO();

  // 1. Today's highest-confidence real-value sharp pick
  const todaySharp = sharpPicks
    .filter(
      (p) =>
        p.isRealValue &&
        p.calibratedConfidence !== null &&
        p.gameTime !== null &&
        torontoGameDate(p.gameTime) === today
    )
    .sort((a, b) => (b.calibratedConfidence ?? 0) - (a.calibratedConfidence ?? 0));

  if (todaySharp.length > 0) {
    const p = todaySharp[0];
    return {
      awayTeam: p.awayTeam,
      homeTeam: p.homeTeam,
      pick: p.pick,
      market: p.market,
      confidence: p.calibratedConfidence,
      gameTime: p.gameTime,
      source: "sharp",
    };
  }

  // 2. Today's best safe-zone pick
  const todaySafe = safeZone.find(
    (p) =>
      p.balancedPick !== null &&
      p.gameTime !== null &&
      torontoGameDate(p.gameTime!) === today
  );
  if (todaySafe) {
    return {
      awayTeam: todaySafe.awayTeam,
      homeTeam: todaySafe.homeTeam,
      pick: todaySafe.balancedPick!,
      market: "safe_balanced",
      confidence: todaySafe.balancedProb,
      gameTime: todaySafe.gameTime,
      source: "safe",
    };
  }

  // 3. Next upcoming qualifying sharp pick (future date, labeled)
  const nextSharp = sharpPicks
    .filter((p) => p.isRealValue && p.calibratedConfidence !== null)
    .sort((a, b) => (b.calibratedConfidence ?? 0) - (a.calibratedConfidence ?? 0));
  if (nextSharp.length > 0) {
    const p = nextSharp[0];
    return {
      awayTeam: p.awayTeam,
      homeTeam: p.homeTeam,
      pick: p.pick,
      market: p.market,
      confidence: p.calibratedConfidence,
      gameTime: p.gameTime,
      source: "sharp",
      dateLabel: futureDateLabel(p.gameTime),
    };
  }

  // 4. Next safe-zone pick (future, labeled)
  const nextSafe = safeZone.find((p) => p.balancedPick !== null);
  if (nextSafe) {
    return {
      awayTeam: nextSafe.awayTeam,
      homeTeam: nextSafe.homeTeam,
      pick: nextSafe.balancedPick!,
      market: "safe_balanced",
      confidence: nextSafe.balancedProb,
      gameTime: nextSafe.gameTime,
      source: "safe",
      dateLabel: futureDateLabel(nextSafe.gameTime),
    };
  }

  return null;
}

// ─── Build deduplicated game list for live polling ────────────────────────────

function buildGameList(
  sharpPicks: MLBSharpPick[],
  safeZone: MLBSafeZonePick[],
  playerProps: MLBPlayerProp[]
): GameInfo[] {
  const seen = new Map<string, GameInfo>();
  for (const p of sharpPicks) {
    if (!seen.has(p.gameId))
      seen.set(p.gameId, {
        gameId: p.gameId,
        homeTeam: p.homeTeam,
        awayTeam: p.awayTeam,
        gameTime: p.gameTime,
      });
  }
  for (const p of safeZone) {
    if (!seen.has(p.gameId))
      seen.set(p.gameId, {
        gameId: p.gameId,
        homeTeam: p.homeTeam,
        awayTeam: p.awayTeam,
        gameTime: p.gameTime,
      });
  }
  for (const p of playerProps) {
    if (!seen.has(p.gameId))
      seen.set(p.gameId, {
        gameId: p.gameId,
        homeTeam: p.homeTeam,
        awayTeam: p.awayTeam,
        gameTime: p.gameTime,
      });
  }
  return [...seen.values()];
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default async function LandingPageRoute({
  searchParams,
}: {
  searchParams: Promise<{ admin?: string }>;
}) {
  const params = await searchParams;
  const isInternalPreview = !LANDING_PAGE_ENABLED;
  const isAdminPreview = isInternalPreview && (ADMIN_PREVIEW || params.admin === "1");

  const [sharpPicks, safeZone] = await Promise.all([
    getMLBSharpPicks(),
    getMLBSafeZone(),
  ]);

  const featuredPick = selectFeaturedPick(sharpPicks, safeZone);

  let adminData: AdminPreviewData | null = null;
  if (isAdminPreview) {
    const [playerProps, diagnostics] = await Promise.all([
      getMLBPlayerProps(),
      getMLBDiagnostics(),
    ]);
    adminData = {
      sharpPicks,
      safeZone,
      playerProps,
      gradedPicks: diagnostics.picks,
      allGames: buildGameList(sharpPicks, safeZone, playerProps),
    };
  }

  return (
    <LandingPage
      featuredPick={featuredPick}
      isInternalPreview={isInternalPreview}
      adminData={adminData}
    />
  );
}
