type BadgeVariant = "elite" | "accent" | "watch" | "reject" | "muted";

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  elite: "bg-elite/15 text-elite border-elite/30",
  accent: "bg-accent-2/15 text-accent-2 border-accent-2/30",
  watch: "bg-watch/15 text-watch border-watch/30",
  reject: "bg-reject/15 text-reject border-reject/30",
  muted: "bg-white/5 text-muted border-border-strong",
};

export function Badge({
  children,
  variant = "muted",
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${VARIANT_CLASSES[variant]}`}
    >
      {children}
    </span>
  );
}

export function tierVariant(tier: string | null): BadgeVariant {
  switch (tier) {
    case "Elite Value":
      return "elite";
    case "Strong Value":
      return "accent";
    case "Playable Value":
      return "watch";
    default:
      return "muted";
  }
}
