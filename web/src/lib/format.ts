export function formatKickoff(iso: string | null): string {
  if (!iso) return "Kickoff TBD";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "Kickoff TBD";

  const formatted = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Toronto",
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);

  return `${formatted} ET`;
}

export function formatPercent(value: number | null, digits = 1): string {
  if (value === null) return "—";
  return `${value.toFixed(digits)}%`;
}

export function formatFirstPitch(iso: string | null): string {
  if (!iso) return "First pitch TBD";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "First pitch TBD";
  const formatted = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Toronto",
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
  return `${formatted} ET`;
}

export function formatSignedPercent(value: number | null, digits = 1): string {
  if (value === null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}%`;
}
