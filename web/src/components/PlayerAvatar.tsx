"use client";

import { useState } from "react";

function initials(name: string | null): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0][0]?.toUpperCase() ?? "?";
  return ((parts[0][0] ?? "") + (parts.at(-1)?.[0] ?? "")).toUpperCase();
}

function InitialsAvatar({ name, size }: { name: string | null; size: number }) {
  return (
    <span
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-bg-2 border border-border text-[10px] font-bold text-muted"
      style={{ width: size, height: size }}
    >
      {initials(name)}
    </span>
  );
}

export function PlayerAvatar({
  playerMlbId,
  playerName,
  size = 32,
}: {
  playerMlbId: number | null;
  playerName: string | null;
  size?: number;
}) {
  const [failed, setFailed] = useState(false);

  if (!playerMlbId || failed) {
    return <InitialsAvatar name={playerName} size={size} />;
  }

  return (
    <img
      src={`https://midfield.mlbstatic.com/v1/people/${playerMlbId}/spots/120`}
      alt={playerName ?? "Player"}
      width={size}
      height={size}
      className="inline-block shrink-0 rounded-full object-cover"
      style={{ width: size, height: size }}
      onError={() => setFailed(true)}
    />
  );
}
