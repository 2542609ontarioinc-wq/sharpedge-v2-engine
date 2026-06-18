type ProbabilityBarVariant = "accent" | "elite";

const FILL_CLASSES: Record<ProbabilityBarVariant, string> = {
  accent: "bg-accent-2",
  elite: "bg-elite",
};

export function ProbabilityBar({
  value,
  variant = "accent",
}: {
  value: number | null;
  variant?: ProbabilityBarVariant;
}) {
  const pct = value === null ? 0 : Math.max(0, Math.min(100, value));

  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className={`h-full rounded-full ${FILL_CLASSES[variant]}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
