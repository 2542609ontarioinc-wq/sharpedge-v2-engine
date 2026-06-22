"use client";

export function fmtDateOption(d: string): string {
  const [y, m, day] = d.split("-").map(Number);
  return new Date(y, m - 1, day).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function DateSelector({
  dates,
  selected,
  onChange,
  showLast7 = false,
}: {
  dates: string[];
  selected: string;
  onChange: (v: string) => void;
  showLast7?: boolean;
}) {
  if (dates.length <= 1) return null;
  return (
    <div className="mb-4 flex items-center gap-2">
      <span className="text-xs text-muted/60">Date</span>
      <select
        value={selected}
        onChange={(e) => onChange(e.target.value)}
        className="cursor-pointer rounded-lg border border-border bg-bg-2 px-2.5 py-1 text-xs text-ink transition-colors hover:border-border-strong focus:outline-none focus:ring-1 focus:ring-accent/40"
      >
        <option value="all">All dates</option>
        {showLast7 && <option value="last7">Last 7 days</option>}
        {dates.map((d) => (
          <option key={d} value={d}>
            {fmtDateOption(d)}
          </option>
        ))}
      </select>
    </div>
  );
}
