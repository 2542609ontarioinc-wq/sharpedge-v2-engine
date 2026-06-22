"use client";

// IMPORTANT: This component is a VISUAL DEV PREVIEW only.
// It uses NO Supabase session, performs NO subscription check, and grants NO real access.
// Before launch: replace with Supabase Auth middleware + server-side subscription gate.

import { useLiveScores } from "@/hooks/useLiveScores";
import { MLBSubscriberView } from "./MLBSubscriberView";
import type { AdminPreviewData } from "@/app/landing/page";

export function LandingAdminPreview({ data }: { data: AdminPreviewData }) {
  const liveState = useLiveScores(data.allGames);

  return (
    <section className="border-t-4 border-watch/50 bg-watch/5 px-4 py-10 sm:px-6">
      <div className="mx-auto max-w-5xl">
        {/* Admin ribbon */}
        <div className="mb-6 rounded-xl border border-watch/50 bg-watch/10 px-4 py-3">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 text-xl">⚠️</span>
            <div>
              <p className="text-sm font-bold text-watch">
                ADMIN PREVIEW — not a real session
              </p>
              <p className="mt-1 text-xs leading-relaxed text-muted">
                This is a visual dev view of the subscriber experience. No Supabase session exists.
                No subscription has been verified. All picks/data are the same as the internal app.{" "}
                <span className="font-semibold text-watch">
                  Replace with Supabase Auth + subscription middleware before this goes live.
                </span>{" "}
                Access via <code className="rounded bg-bg-2 px-1 text-ink">?admin=1</code> or{" "}
                <code className="rounded bg-bg-2 px-1 text-ink">ADMIN_PREVIEW = true</code> in{" "}
                <code className="rounded bg-bg-2 px-1 text-ink">app/landing/page.tsx</code>.
              </p>
            </div>
          </div>
        </div>

        <div className="mb-4 flex items-center gap-2">
          <h2 className="text-lg font-bold text-ink">Subscriber experience preview</h2>
          <span className="rounded-sm bg-watch/20 px-1.5 py-0.5 text-[9px] font-bold text-watch">
            INTERNAL
          </span>
        </div>

        <MLBSubscriberView
          sharpPicks={data.sharpPicks}
          safeZone={data.safeZone}
          playerProps={data.playerProps}
          liveState={liveState}
          gradedPicks={data.gradedPicks}
        />
      </div>
    </section>
  );
}
