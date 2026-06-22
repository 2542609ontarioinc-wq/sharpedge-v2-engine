// ─── INTERNAL GATE ──────────────────────────────────────────────────────────
// Flip to `true` when ready to make /landing publicly accessible.
// While false, the page renders with an "INTERNAL PREVIEW" ribbon.
// Mirror of SUBSCRIBER_TAB_INTERNAL in PicksView.tsx.
const LANDING_PAGE_ENABLED = false;
// ────────────────────────────────────────────────────────────────────────────

import { getMLBSharpPicks, getMLBSafeZone } from "@/lib/data";
import { LandingPage } from "@/components/LandingPage";
import type { MLBSafeZonePick, MLBSharpPick } from "@/lib/types";

export const revalidate = 60;

export type FeaturedPick = {
  awayTeam: string;
  homeTeam: string;
  pick: string;
  market: string;
  confidence: number | null;
  gameTime: string | null;
  source: "sharp" | "safe";
};

function selectFeaturedPick(
  sharpPicks: MLBSharpPick[],
  safeZone: MLBSafeZonePick[]
): FeaturedPick | null {
  // Prefer the highest-confidence real-value sharp pick
  const qualifying = sharpPicks
    .filter((p) => p.isRealValue && p.calibratedConfidence !== null)
    .sort((a, b) => (b.calibratedConfidence ?? 0) - (a.calibratedConfidence ?? 0));

  if (qualifying.length > 0) {
    const p = qualifying[0];
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

  // Fall back to the first safe-zone balanced pick
  const safe = safeZone.find((p) => p.balancedPick !== null);
  if (safe) {
    return {
      awayTeam: safe.awayTeam,
      homeTeam: safe.homeTeam,
      pick: safe.balancedPick!,
      market: "safe_balanced",
      confidence: safe.balancedProb,
      gameTime: safe.gameTime,
      source: "safe",
    };
  }

  return null;
}

export default async function LandingPageRoute() {
  const [sharpPicks, safeZone] = await Promise.all([
    getMLBSharpPicks(),
    getMLBSafeZone(),
  ]);

  const featuredPick = selectFeaturedPick(sharpPicks, safeZone);

  return (
    <LandingPage
      featuredPick={featuredPick}
      isInternalPreview={!LANDING_PAGE_ENABLED}
    />
  );
}
