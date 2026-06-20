const TEAM_ID_MAP: Record<string, number> = {
  // Arizona Diamondbacks
  "arizona diamondbacks": 109, "diamondbacks": 109, "az diamondbacks": 109, "ari": 109, "az": 109,
  // Atlanta Braves
  "atlanta braves": 144, "braves": 144, "atl": 144,
  // Baltimore Orioles
  "baltimore orioles": 110, "orioles": 110, "bal": 110,
  // Boston Red Sox
  "boston red sox": 111, "red sox": 111, "bos": 111,
  // Chicago Cubs
  "chicago cubs": 112, "cubs": 112, "chc": 112,
  // Chicago White Sox
  "chicago white sox": 145, "white sox": 145, "cws": 145, "chw": 145,
  // Cincinnati Reds
  "cincinnati reds": 113, "reds": 113, "cin": 113,
  // Cleveland Guardians
  "cleveland guardians": 114, "guardians": 114, "cle": 114,
  // Colorado Rockies
  "colorado rockies": 115, "rockies": 115, "col": 115,
  // Detroit Tigers
  "detroit tigers": 116, "tigers": 116, "det": 116,
  // Houston Astros
  "houston astros": 117, "astros": 117, "hou": 117,
  // Kansas City Royals
  "kansas city royals": 118, "royals": 118, "kc": 118, "kcr": 118,
  // Los Angeles Angels
  "los angeles angels": 108, "angels": 108, "laa": 108, "la angels": 108,
  // Los Angeles Dodgers
  "los angeles dodgers": 119, "dodgers": 119, "lad": 119, "la dodgers": 119,
  // Miami Marlins
  "miami marlins": 146, "marlins": 146, "mia": 146,
  // Milwaukee Brewers
  "milwaukee brewers": 158, "brewers": 158, "mil": 158,
  // Minnesota Twins
  "minnesota twins": 142, "twins": 142, "min": 142,
  // New York Mets
  "new york mets": 121, "mets": 121, "nym": 121, "ny mets": 121,
  // New York Yankees
  "new york yankees": 147, "yankees": 147, "nyy": 147, "ny yankees": 147,
  // Athletics (Oakland / Sacramento)
  "oakland athletics": 133, "sacramento athletics": 133, "athletics": 133, "ath": 133, "oak": 133,
  // Philadelphia Phillies
  "philadelphia phillies": 143, "phillies": 143, "phi": 143,
  // Pittsburgh Pirates
  "pittsburgh pirates": 134, "pirates": 134, "pit": 134,
  // San Diego Padres
  "san diego padres": 135, "padres": 135, "sd": 135, "sdp": 135,
  // San Francisco Giants
  "san francisco giants": 137, "giants": 137, "sf": 137, "sfg": 137,
  // Seattle Mariners
  "seattle mariners": 136, "mariners": 136, "sea": 136,
  // St. Louis Cardinals
  "st. louis cardinals": 138, "st louis cardinals": 138, "cardinals": 138, "stl": 138,
  // Tampa Bay Rays
  "tampa bay rays": 139, "rays": 139, "tb": 139, "tbr": 139,
  // Texas Rangers
  "texas rangers": 140, "rangers": 140, "tex": 140,
  // Toronto Blue Jays
  "toronto blue jays": 141, "blue jays": 141, "tor": 141,
  // Washington Nationals
  "washington nationals": 120, "nationals": 120, "wsh": 120, "was": 120,
};

export function mlbTeamId(name: string): number | null {
  if (!name) return null;
  const key = name.toLowerCase().trim();
  if (TEAM_ID_MAP[key] !== undefined) return TEAM_ID_MAP[key];
  // Fallback: match last word (nickname)
  const last = key.split(/\s+/).at(-1) ?? "";
  return TEAM_ID_MAP[last] ?? null;
}

export function mlbLogoUrl(name: string): string | null {
  const id = mlbTeamId(name);
  return id !== null ? `https://www.mlbstatic.com/team-logos/${id}.svg` : null;
}
