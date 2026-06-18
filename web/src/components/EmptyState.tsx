export function EmptyState({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border-strong bg-surface/40 px-6 py-16 text-center">
      <p className="text-base font-semibold text-ink">{title}</p>
      <p className="mt-1.5 max-w-sm text-sm text-muted">{subtitle}</p>
    </div>
  );
}
