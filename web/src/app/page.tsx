import { Header } from "@/components/Header";
import { PicksView } from "@/components/PicksView";
import { getSharpPicks, getSafeZone, getTrackRecord } from "@/lib/data";

export const revalidate = 30;

export default async function Home() {
  const [sharpPicks, safeZone, trackRecord] = await Promise.all([
    getSharpPicks(),
    getSafeZone(),
    getTrackRecord(),
  ]);

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <PicksView sharpPicks={sharpPicks} safeZone={safeZone} trackRecord={trackRecord} />
      </main>
    </div>
  );
}
