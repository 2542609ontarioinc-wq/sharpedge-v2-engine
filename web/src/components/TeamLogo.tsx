"use client";

import { useState } from "react";
import { mlbLogoUrl } from "@/lib/mlb-teams";

export function TeamLogo({ team, size = 28 }: { team: string; size?: number }) {
  const [failed, setFailed] = useState(false);
  const url = mlbLogoUrl(team);

  if (!url || failed) return null;

  return (
    <img
      src={url}
      alt={team}
      width={size}
      height={size}
      className="inline-block shrink-0 object-contain"
      style={{ width: size, height: size }}
      onError={() => setFailed(true)}
    />
  );
}
