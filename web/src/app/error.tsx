"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-lg font-semibold text-ink">Couldn&apos;t load picks</p>
      <p className="max-w-sm text-sm text-muted">
        {error.message || "Something went wrong talking to Supabase."}
      </p>
      <button
        type="button"
        onClick={reset}
        className="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-bg"
      >
        Try again
      </button>
    </div>
  );
}
