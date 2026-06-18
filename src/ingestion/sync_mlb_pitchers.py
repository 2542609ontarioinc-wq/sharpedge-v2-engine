"""
Sync MLB probable starting pitchers from the free MLB Stats API
(statsapi.mlb.com/api/v1) for upcoming games.

API-Sports baseball does NOT carry pitcher data — this uses a separate,
free, keyless source.  Runs daily after sync_mlb_games so game_ids exist.

For each game in the next 3 days:
  1. Fetch probable pitchers from the MLB Stats API schedule endpoint.
  2. Match the MLB API game to our Supabase game by date + normalized team names.
  3. Fetch season pitching stats for each probable pitcher.
  4. Compute shrunk RA9 index: (pitcher_ra9 / 4.5) shrunk toward 1.0 with K=5 starts.
  5. Upsert into mlb_pitchers (on_conflict: game_id, side).
"""
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

TORONTO = ZoneInfo("America/Toronto")
SPORT_KEY = "baseball_mlb"
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

LEAGUE_AVG_RA9 = 4.5
SHRINK_K = 5

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _norm(name):
    """Normalize team name for matching (handles 'St. Louis' vs 'St.Louis', etc.)."""
    n = (name or "").lower().strip()
    n = n.replace(".", " ")
    n = re.sub(r'\s+', ' ', n)
    return n.strip()


def _safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _shrunk_ra9_index(ra9, games_started):
    raw = ra9 / LEAGUE_AVG_RA9
    w = games_started / (games_started + SHRINK_K)
    return round(max(0.4, min(2.5, w * raw + (1 - w) * 1.0)), 4)


def _fetch_schedule(date_str):
    r = requests.get(
        f"{MLB_API_BASE}/schedule",
        params={"sportId": 1, "date": date_str, "hydrate": "probablePitcher,team"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _fetch_pitcher_stats(pitcher_id, season):
    r = requests.get(
        f"{MLB_API_BASE}/people/{pitcher_id}/stats",
        params={"stats": "season", "season": season, "group": "pitching"},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    for group in data.get("stats", []):
        splits = group.get("splits", [])
        if splits:
            return splits[0].get("stat", {})
    return {}


def main():
    today = datetime.now(TORONTO).date()
    season = today.year
    dates = [(today + timedelta(days=d)).isoformat() for d in range(4)]

    # Build lookup: (norm_home, norm_away, date) → Supabase game uuid
    sb_games = (
        supabase.table("games")
        .select("id,game_date,home_team_name,away_team_name")
        .eq("sport_key", SPORT_KEY)
        .gte("game_date", today.isoformat())
        .lte("game_date", (today + timedelta(days=3)).isoformat())
        .execute()
        .data
    )
    sb_lookup = {}
    for g in sb_games:
        key = (_norm(g["home_team_name"]), _norm(g["away_team_name"]), g["game_date"])
        sb_lookup[key] = g["id"]

    saved = matched = 0

    for date_str in dates:
        try:
            data = _fetch_schedule(date_str)
        except Exception as e:
            print(f"  {date_str}: schedule fetch failed: {e}")
            continue

        for d in data.get("dates", []):
            for game in d.get("games", []):
                if game.get("gameType") != "R":
                    continue

                teams = game.get("teams", {})
                home_name = teams.get("home", {}).get("team", {}).get("name", "")
                away_name = teams.get("away", {}).get("team", {}).get("name", "")

                key = (_norm(home_name), _norm(away_name), date_str)
                game_id = sb_lookup.get(key)
                if not game_id:
                    continue
                matched += 1

                for side, team_key, team_name in [
                    ("home", "home", home_name),
                    ("away", "away", away_name),
                ]:
                    pp = teams.get(team_key, {}).get("probablePitcher")
                    if not pp:
                        continue

                    pitcher_id = pp.get("id")
                    pitcher_name = pp.get("fullName", "Unknown")

                    try:
                        stats = _fetch_pitcher_stats(pitcher_id, season)
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"  {date_str} {side} {pitcher_name}: stats fetch failed: {e}")
                        stats = {}

                    gs = int(stats.get("gamesStarted") or 0)
                    ra9 = _safe_float(stats.get("runsScoredPer9"))
                    if ra9 is None:
                        ra9 = LEAGUE_AVG_RA9
                        gs = 0

                    shrunk = _shrunk_ra9_index(ra9, gs)

                    row = {
                        "game_id": game_id,
                        "game_date": date_str,
                        "side": side,
                        "team_name": team_name,
                        "pitcher_mlb_id": pitcher_id,
                        "pitcher_name": pitcher_name,
                        "season": season,
                        "era": str(stats.get("era") or ""),
                        "innings_pitched": str(stats.get("inningsPitched") or ""),
                        "runs_per_9": round(ra9, 3),
                        "whip": str(stats.get("whip") or ""),
                        "games_started": gs,
                        "shrunk_ra9_index": shrunk,
                        "raw_stats": stats or {},
                        "synced_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                    }
                    supabase.table("mlb_pitchers").upsert(row, on_conflict="game_id,side").execute()
                    saved += 1
                    print(
                        f"  {date_str} {team_name} ({side}): {pitcher_name} "
                        f"ERA={stats.get('era', '?')} RA9={ra9:.2f} GS={gs} idx={shrunk}"
                    )

    print(f"\n✅ MLB pitchers synced: {saved} entries | {matched} games matched")


if __name__ == "__main__":
    main()
