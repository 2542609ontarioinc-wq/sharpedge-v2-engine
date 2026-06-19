"""
Sync MLB team bullpen (relief pitching) aggregate strength from the free MLB Stats API.

One API call fetches all pitchers' season stats; we filter to relievers
(gamesStarted == 0 or started in < 30% of appearances), aggregate by team,
apply IP-weighted shrinkage toward league average, and upsert to
mlb_bullpen_strength.

Cost: 1 free API call per run (statsapi.mlb.com, keyless).
"""
import re
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MLB_API_BASE = "https://statsapi.mlb.com/api/v1"
LEAGUE_AVG_RA9 = 4.5
SHRINK_IP = 50.0   # IP at which raw index carries 50% weight; ~25–30 team games
SPORT_KEY = "baseball_mlb"


def _norm(name):
    n = (name or "").lower().strip()
    n = n.replace(".", " ")
    n = re.sub(r'\s+', ' ', n)
    return n.strip()


def _parse_ip(ip_str):
    """'95.2' → 95.667 (baseball .X notation: tenths = outs, not decimal thirds)."""
    try:
        parts = str(ip_str).split(".")
        full = int(parts[0])
        outs = int(parts[1]) if len(parts) > 1 else 0
        return full + outs / 3.0
    except Exception:
        return 0.0


def _safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _fetch_all_pitching_stats(season):
    """Single API call: all pitcher season stats for the year."""
    r = requests.get(
        f"{MLB_API_BASE}/stats",
        params={
            "stats": "season",
            "group": "pitching",
            "gameType": "R",
            "season": season,
            "sportId": 1,
            "playerPool": "All",
            "limit": 2000,
        },
        timeout=30,
    )
    r.raise_for_status()
    splits = []
    for stat_group in r.json().get("stats", []):
        splits.extend(stat_group.get("splits", []))
    return splits


def _build_team_name_lookup():
    """Canonical team names from our mlb_team_run_strength table."""
    rows = supabase.table("mlb_team_run_strength").select("team_name").execute().data
    return {_norm(r["team_name"]): r["team_name"] for r in rows}


def main():
    today = datetime.now(ZoneInfo("America/Toronto"))
    season = today.year

    print(f"Fetching MLB pitching stats for {season} (one API call)...")
    try:
        splits = _fetch_all_pitching_stats(season)
    except Exception as e:
        print(f"  API call failed: {e}")
        return

    if not splits:
        print("  No pitching splits returned — skipping.")
        return

    print(f"  {len(splits)} pitcher-season rows received")

    team_name_lookup = _build_team_name_lookup()

    # Aggregate relief stats keyed by MLB team id
    team_stats = defaultdict(lambda: {
        "name": None, "mlb_id": None,
        "ip": 0.0, "er": 0, "r": 0, "bb": 0, "h": 0, "k": 0, "apps": 0,
    })

    for split in splits:
        stat = split.get("stat", {})
        team_info = split.get("team")
        if not team_info:
            continue

        mlb_team_id = team_info.get("id")
        mlb_team_name = team_info.get("name", "")
        gs = _safe_int(stat.get("gamesStarted"))
        gp = _safe_int(stat.get("gamesPlayed"))

        is_reliever = gs == 0 or (gp > 0 and gs / gp < 0.3)
        if not is_reliever:
            continue

        ip = _parse_ip(stat.get("inningsPitched", "0"))
        if ip <= 0:
            continue

        ts = team_stats[mlb_team_id]
        ts["name"] = mlb_team_name
        ts["mlb_id"] = mlb_team_id
        ts["ip"] += ip
        ts["er"] += _safe_int(stat.get("earnedRuns"))
        ts["r"] += _safe_int(stat.get("runs"))
        ts["bb"] += _safe_int(stat.get("baseOnBalls"))
        ts["h"] += _safe_int(stat.get("hits"))
        ts["k"] += _safe_int(stat.get("strikeOuts"))
        ts["apps"] += gp

    if not team_stats:
        print("  No relief data aggregated — skipping.")
        return

    # League-average bullpen RA9 across teams with at least 10 IP
    ra9_values = [
        (ts["r"] / ts["ip"]) * 9.0
        for ts in team_stats.values()
        if ts["ip"] >= 10
    ]
    league_avg_ra9 = sum(ra9_values) / len(ra9_values) if ra9_values else LEAGUE_AVG_RA9

    saved = 0
    for mlb_team_id, ts in sorted(team_stats.items()):
        ip = ts["ip"]
        if ip < 1.0:
            continue

        bullpen_era = round((ts["er"] / ip) * 9.0, 3)
        bullpen_ra9 = round((ts["r"] / ip) * 9.0, 3)
        bullpen_whip = round((ts["bb"] + ts["h"]) / ip, 3)
        bullpen_k9 = round((ts["k"] / ip) * 9.0, 3)

        raw_ra9_index = round(bullpen_ra9 / league_avg_ra9, 4) if league_avg_ra9 > 0 else 1.0

        # Shrink toward 1.0; full credibility at SHRINK_IP innings
        w = ip / (ip + SHRINK_IP)
        shrunk_ra9_index = round(max(0.5, min(2.0, w * raw_ra9_index + (1 - w) * 1.0)), 4)

        canonical_name = team_name_lookup.get(_norm(ts["name"]), ts["name"])

        row = {
            "team_name": canonical_name,
            "team_mlb_id": mlb_team_id,
            "season": season,
            "bullpen_ip": round(ip, 2),
            "bullpen_era": bullpen_era,
            "bullpen_whip": bullpen_whip,
            "bullpen_k9": bullpen_k9,
            "bullpen_ra9": bullpen_ra9,
            "raw_ra9_index": raw_ra9_index,
            "shrunk_ra9_index": shrunk_ra9_index,
            "games_counted": ts["apps"],
            "updated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        }
        supabase.table("mlb_bullpen_strength").upsert(
            row, on_conflict="team_name,season"
        ).execute()
        saved += 1
        print(
            f"  {canonical_name}: RA9={bullpen_ra9:.2f} ERA={bullpen_era:.2f} "
            f"WHIP={bullpen_whip:.2f} K/9={bullpen_k9:.2f} IP={ip:.0f} "
            f"shrunk={shrunk_ra9_index} [w={w:.2f}]"
        )

    print(
        f"\n✅ MLB bullpen strength: {saved} teams | "
        f"league avg bullpen RA9={league_avg_ra9:.2f}"
    )


if __name__ == "__main__":
    main()
