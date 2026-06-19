import { Header } from "@/components/Header";
import { PicksView } from "@/components/PicksView";
import {
  getMLBModelAnalytics,
  getMLBModelLab,
  getMLBPlayerProps,
  getMLBSafeZone,
  getMLBSharpPicks,
  getMLBTrackRecord,
  getSafeZone,
  getSharpPicks,
  getTrackRecord,
} from "@/lib/data";

export const revalidate = 30;

export default async function Home() {
  const [
    sharpPicks,
    safeZone,
    trackRecord,
    mlbSharpPicks,
    mlbSafeZone,
    mlbTrackRecord,
    mlbPlayerProps,
    mlbModelLab,
    mlbModelAnalytics,
  ] = await Promise.all([
    getSharpPicks(),
    getSafeZone(),
    getTrackRecord(),
    getMLBSharpPicks(),
    getMLBSafeZone(),
    getMLBTrackRecord(),
    getMLBPlayerProps(),
    getMLBModelLab(),
    getMLBModelAnalytics(),
  ]);

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <PicksView
          sharpPicks={sharpPicks}
          safeZone={safeZone}
          trackRecord={trackRecord}
          mlbSharpPicks={mlbSharpPicks}
          mlbSafeZone={mlbSafeZone}
          mlbTrackRecord={mlbTrackRecord}
          mlbPlayerProps={mlbPlayerProps}
          mlbModelLab={mlbModelLab}
          mlbModelAnalytics={mlbModelAnalytics}
        />
      </main>
    </div>
  );
}
