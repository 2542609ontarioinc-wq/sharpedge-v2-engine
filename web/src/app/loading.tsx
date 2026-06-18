export default function Loading() {
  return (
    <div className="min-h-screen">
      <div className="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur">
        <div className="mx-auto max-w-5xl px-4 py-4 sm:px-6">
          <div className="h-5 w-32 animate-pulse rounded bg-white/10" />
        </div>
      </div>
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <div className="mb-6 h-10 w-56 animate-pulse rounded-full bg-white/10" />
        <div className="grid gap-4 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-56 animate-pulse rounded-2xl border border-border bg-surface"
            />
          ))}
        </div>
      </main>
    </div>
  );
}
