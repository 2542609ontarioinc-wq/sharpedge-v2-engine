"use client";

import { useState, useCallback } from "react";
import { mlbLogoUrl } from "@/lib/mlb-teams";
import { LandingAdminPreview } from "./LandingAdminPreview";
import type { AdminPreviewData, FeaturedPick } from "@/app/landing/page";

// ─── Helpers ─────────────────────────────────────────────────────────────────

const MARKET_LABELS: Record<string, string> = {
  moneyline: "Moneyline",
  totals: "Totals",
  run_line: "Run Line",
  safe_balanced: "Safe Pick",
  safe_banker: "Banker Pick",
};

function formatGameTime(iso: string | null): string {
  if (!iso) return "Game time TBD";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "Game time TBD";
  return (
    new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Toronto",
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(d) + " ET"
  );
}

// ─── Coming-Soon Modal ────────────────────────────────────────────────────────

function ComingSoonModal({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="relative max-w-sm w-full rounded-2xl border border-border-strong bg-bg-2 p-8 text-center shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 text-4xl">⚡</div>
        <h2 className="mb-2 text-xl font-bold text-ink">Coming soon</h2>
        <p className="text-sm text-muted leading-relaxed">
          Internal preview only — not yet open to the public.
          <br />
          Check back soon.
        </p>
        <button
          onClick={onClose}
          className="mt-6 rounded-xl bg-accent/10 border border-accent/30 px-6 py-2.5 text-sm font-semibold text-accent hover:bg-accent/20 transition-colors"
        >
          Got it
        </button>
      </div>
    </div>
  );
}

// ─── Internal Preview Ribbon ─────────────────────────────────────────────────

function InternalBanner({ adminMode }: { adminMode: boolean }) {
  return (
    <div className="sticky top-0 z-40 bg-watch/20 border-b border-watch/40 px-4 py-2 text-center">
      <p className="text-xs font-semibold text-watch">
        INTERNAL PREVIEW — Flip{" "}
        <code className="font-mono text-ink/80">LANDING_PAGE_ENABLED = true</code>{" "}
        in <code className="font-mono text-ink/80">app/landing/page.tsx</code> to go live
        {adminMode && (
          <span className="ml-3 text-watch/70">
            · Admin preview active (<code className="font-mono text-ink/70">?admin=1</code>)
          </span>
        )}
      </p>
    </div>
  );
}

// ─── Nav Bar ─────────────────────────────────────────────────────────────────

function LandingNav({ onComingSoon }: { onComingSoon: () => void }) {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-reject opacity-60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-reject" />
          </span>
          <span className="text-lg font-bold tracking-tight text-ink">
            Sharp<span className="text-reject">Edge</span>
          </span>
        </div>

        {/* Auth stubs */}
        <div className="flex items-center gap-2">
          <button
            onClick={onComingSoon}
            className="rounded-lg px-4 py-2 text-sm font-medium text-muted hover:text-ink transition-colors"
          >
            Sign in
          </button>
          <button
            onClick={onComingSoon}
            className="rounded-xl bg-reject px-4 py-2 text-sm font-semibold text-white hover:bg-reject/80 transition-colors"
          >
            Sign up
          </button>
        </div>
      </div>
    </header>
  );
}

// ─── Hero ─────────────────────────────────────────────────────────────────────

function LandingHero({ onComingSoon }: { onComingSoon: () => void }) {
  const scrollToFreePick = () => {
    document.getElementById("free-pick")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative overflow-hidden px-4 py-24 sm:py-32 text-center">
      <div className="pointer-events-none absolute inset-0 flex items-start justify-center">
        <div className="h-96 w-96 rounded-full bg-reject/8 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-4xl">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-1.5 text-xs font-medium text-muted">
          <span className="h-1.5 w-1.5 rounded-full bg-elite" />
          MLB · Soccer · Probability Engine
        </div>

        <h1 className="mb-6 text-4xl font-extrabold leading-tight tracking-tight text-ink sm:text-5xl lg:text-6xl">
          Sports predictions that{" "}
          <span className="text-reject">judge themselves</span> honestly
        </h1>

        <p className="mx-auto mb-10 max-w-2xl text-lg text-muted leading-relaxed">
          We build probability models for MLB and soccer, then grade every call
          against the closing line — the sharpest benchmark in sports betting.
          No cherry-picked results. Every pick, every grade, published.
        </p>

        <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={onComingSoon}
            className="w-full sm:w-auto rounded-xl bg-reject px-8 py-3.5 text-sm font-semibold text-white hover:bg-reject/80 transition-colors shadow-lg shadow-reject/20"
          >
            Start free
          </button>
          <button
            onClick={scrollToFreePick}
            className="w-full sm:w-auto rounded-xl border border-border bg-surface px-8 py-3.5 text-sm font-semibold text-ink hover:border-border-strong hover:bg-surface-2 transition-colors"
          >
            See today&rsquo;s free pick ↓
          </button>
        </div>
      </div>
    </section>
  );
}

// ─── Stats Row ────────────────────────────────────────────────────────────────

function LandingStats() {
  const stats = [
    { value: "6", label: "Models tracked" },
    { value: "2", label: "Sports covered" },
    { value: "CLV", label: "Our true judge" },
    { value: "100%", label: "Transparent grades" },
  ];

  return (
    <section className="border-y border-border bg-surface/50">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <p className="text-3xl font-extrabold text-reject">{s.value}</p>
              <p className="mt-1 text-xs font-medium text-muted">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Who We Are ───────────────────────────────────────────────────────────────

function LandingAbout() {
  return (
    <section className="px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <h2 className="mb-4 text-2xl font-bold text-ink sm:text-3xl">Who we are</h2>
        <div className="space-y-4 text-muted leading-relaxed">
          <p>
            SharpEdge is an independent analytics project — not a sportsbook,
            not a tout service, not affiliated with any league. We build
            statistical models for MLB and soccer and publish their outputs
            openly.
          </p>
          <p>
            Our philosophy is{" "}
            <span className="font-semibold text-ink">70% market, 30% model</span>: closing-line
            value (CLV) is the most honest measure of pick quality. A pick that beats the close is
            good; a pick that doesn&rsquo;t isn&rsquo;t, regardless of the outcome.
          </p>
          <p>
            We publish wins and losses. Our models are unproven in real money —
            all historical results are{" "}
            <span className="font-semibold text-watch">paper only</span>. We will not claim an
            edge we haven&rsquo;t earned.
          </p>
        </div>
      </div>
    </section>
  );
}

// ─── Free Public Pick ─────────────────────────────────────────────────────────

function TeamLogoOrInitial({ team, size = 36 }: { team: string; size?: number }) {
  const [failed, setFailed] = useState(false);
  const url = mlbLogoUrl(team);

  if (!url || failed) {
    return (
      <div
        className="flex items-center justify-center rounded-full bg-surface border border-border text-xs font-bold text-muted"
        style={{ width: size, height: size }}
      >
        {team.slice(0, 2).toUpperCase()}
      </div>
    );
  }

  return (
    <img
      src={url}
      alt={team}
      width={size}
      height={size}
      className="object-contain"
      style={{ width: size, height: size }}
      onError={() => setFailed(true)}
    />
  );
}

function LandingFreePick({ pick }: { pick: FeaturedPick | null }) {
  const isFuture = Boolean(pick?.dateLabel);

  return (
    <section id="free-pick" className="scroll-mt-20 px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-2xl">
        <div className="mb-2 flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-elite opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-elite" />
          </span>
          <span className="text-xs font-semibold uppercase tracking-widest text-elite">
            {pick?.dateLabel ?? "Today's free pick"}
          </span>
        </div>

        <h2 className="mb-6 text-2xl font-bold text-ink sm:text-3xl">
          {isFuture ? "Upcoming free pick" : "Free public pick"}
        </h2>

        {isFuture && (
          <p className="mb-4 rounded border border-border bg-surface/60 px-3 py-2 text-xs text-muted/70">
            No qualifying pick available for today yet. Showing the next upcoming pick — check back
            closer to game time for today&rsquo;s slate.
          </p>
        )}

        {pick ? (
          <div className="rounded-2xl border-2 border-elite/40 bg-elite/5 p-6 shadow-lg shadow-elite/5">
            {/* Teams */}
            <div className="mb-5 flex items-center gap-4">
              <div className="flex items-center gap-2">
                <TeamLogoOrInitial team={pick.awayTeam} size={40} />
                <span className="text-sm font-medium text-ink">{pick.awayTeam}</span>
              </div>
              <span className="text-xs font-bold text-muted">@</span>
              <div className="flex items-center gap-2">
                <TeamLogoOrInitial team={pick.homeTeam} size={40} />
                <span className="text-sm font-medium text-ink">{pick.homeTeam}</span>
              </div>
            </div>

            {/* Pick */}
            <div className="mb-4 rounded-xl border border-elite/20 bg-bg-2/60 px-5 py-4">
              <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-elite">
                {MARKET_LABELS[pick.market] ?? pick.market}
              </div>
              <p className="text-2xl font-bold text-ink">{pick.pick}</p>
              {pick.confidence !== null && (
                <p className="mt-1 text-sm text-muted">
                  Model confidence:{" "}
                  <span className="font-semibold text-ink">{pick.confidence.toFixed(1)}%</span>
                </p>
              )}
              <p className="mt-1 text-xs text-muted">{formatGameTime(pick.gameTime)}</p>
            </div>

            {/* Responsible gambling */}
            <p className="text-xs text-muted/70 leading-relaxed">
              Unproven model · paper only · 19+ · gamble responsibly · ConnexOntario{" "}
              <span className="font-medium text-muted">1-866-531-2600</span>
            </p>
          </div>
        ) : (
          <div className="rounded-2xl border-2 border-border bg-surface/50 p-8 text-center">
            <p className="text-sm text-muted">No qualifying pick available today.</p>
            <p className="mt-1 text-xs text-muted/60">
              The engine only publishes picks it believes in.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

// ─── Pricing ─────────────────────────────────────────────────────────────────

type PricingTier = {
  name: string;
  price: string;
  description: string;
  features: string[];
  cta: string;
  highlighted: boolean;
};

const PRICING_TIERS: PricingTier[] = [
  {
    name: "Free",
    price: "$—",
    description: "One free pick per day, no card required.",
    features: [
      "1 free pick per day",
      "MLB + soccer coverage",
      "Pick grade published after game",
      "No account needed",
    ],
    cta: "Get started free",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$—",
    description: "Full daily slate for serious paper traders.",
    features: [
      "Full sharp-pick slate",
      "Safe-zone coverage",
      "Confidence & CLV scores",
      "Live track record",
      "Email alerts",
    ],
    cta: "Choose Pro",
    highlighted: true,
  },
  {
    name: "Elite",
    price: "$—",
    description: "Model-lab access and deep analytics.",
    features: [
      "Everything in Pro",
      "Model Lab (6 models)",
      "Per-model analytics",
      "Player props",
      "Priority support",
    ],
    cta: "Choose Elite",
    highlighted: false,
  },
];

function LandingPricing({ onComingSoon }: { onComingSoon: () => void }) {
  return (
    <section className="px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 text-center">
          <h2 className="mb-3 text-2xl font-bold text-ink sm:text-3xl">Simple, honest pricing</h2>
          <p className="text-muted">
            Prices finalized before launch.{" "}
            <span className="text-watch font-medium">$— placeholders</span> — we&rsquo;ll fill
            these in.
          </p>
        </div>

        <div className="grid gap-6 sm:grid-cols-3">
          {PRICING_TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`relative flex flex-col rounded-2xl border p-6 ${
                tier.highlighted
                  ? "border-watch/50 bg-watch/5 shadow-lg shadow-watch/10"
                  : "border-border bg-surface/50"
              }`}
            >
              {tier.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="rounded-full bg-watch px-3 py-1 text-xs font-bold text-bg">
                    Most popular
                  </span>
                </div>
              )}

              <div className="mb-5">
                <h3
                  className={`text-lg font-bold ${
                    tier.highlighted ? "text-watch" : "text-ink"
                  }`}
                >
                  {tier.name}
                </h3>
                <div className="mt-1 flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold text-ink">{tier.price}</span>
                  <span className="text-xs text-muted">/mo</span>
                </div>
                <p className="mt-2 text-xs text-muted">{tier.description}</p>
              </div>

              <ul className="mb-6 flex-1 space-y-2.5">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-muted">
                    <span
                      className={`mt-0.5 shrink-0 font-bold ${
                        tier.highlighted ? "text-watch" : "text-elite"
                      }`}
                    >
                      ✓
                    </span>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={onComingSoon}
                className={`w-full rounded-xl py-2.5 text-sm font-semibold transition-colors ${
                  tier.highlighted
                    ? "bg-watch text-bg hover:bg-watch/80"
                    : "border border-border bg-surface text-ink hover:border-border-strong hover:bg-surface-2"
                }`}
              >
                {tier.cta}
              </button>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Footer ───────────────────────────────────────────────────────────────────

function LandingFooter() {
  return (
    <footer className="border-t border-border px-4 py-10 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-reject" />
            <span className="text-sm font-bold tracking-tight text-ink">
              Sharp<span className="text-reject">Edge</span>
            </span>
          </div>
          <nav className="flex gap-4 text-xs text-muted">
            <button className="hover:text-ink transition-colors">Terms (coming soon)</button>
            <button className="hover:text-ink transition-colors">Privacy (coming soon)</button>
          </nav>
        </div>

        <div className="space-y-2 text-xs text-muted/70 leading-relaxed">
          <p>
            <strong className="text-muted">19+ only.</strong> Sports betting involves risk. Our
            models are unproven — all published results are paper-trade simulations only. Never bet
            more than you can afford to lose.
          </p>
          <p>
            If you or someone you know has a gambling problem, call ConnexOntario at{" "}
            <span className="font-medium text-muted">1-866-531-2600</span> or visit{" "}
            <span className="font-medium text-muted">connexontario.ca</span>.
          </p>
          <p>
            SharpEdge is an independent analytics project. Not affiliated with MLB, MLS, any league,
            any sportsbook, or any governing body. No financial advice is given or implied.
          </p>
        </div>
      </div>
    </footer>
  );
}

// ─── Root Component ───────────────────────────────────────────────────────────

export function LandingPage({
  featuredPick,
  isInternalPreview,
  adminData,
}: {
  featuredPick: FeaturedPick | null;
  isInternalPreview: boolean;
  adminData: AdminPreviewData | null;
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const openModal = useCallback(() => setModalOpen(true), []);
  const closeModal = useCallback(() => setModalOpen(false), []);

  return (
    <div className="min-h-screen">
      {isInternalPreview && <InternalBanner adminMode={adminData !== null} />}
      <LandingNav onComingSoon={openModal} />

      <main>
        <LandingHero onComingSoon={openModal} />
        <LandingStats />
        <LandingAbout />
        <LandingFreePick pick={featuredPick} />
        <LandingPricing onComingSoon={openModal} />
      </main>

      <LandingFooter />

      {adminData && <LandingAdminPreview data={adminData} />}

      {modalOpen && <ComingSoonModal onClose={closeModal} />}
    </div>
  );
}
