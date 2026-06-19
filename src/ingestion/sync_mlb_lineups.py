"""
Sync confirmed MLB batting lineups from the MLB Stats API.

For each upcoming game (next 3 days):
  1. Fetch schedule with hydrate=lineups,team — free, keyless MLB Stats API.
  2. Match games to Supabase game_ids by date + normalised team name.
  3. For each batter in the confirmed lineup (positions 1-9), fetch season
     hitting stats (hits, runs, RBI, games_played).
  4. Compute avg_hrr_per_game = (H + R + RBI) / games_played.
  5. Upsert into mlb_lineups (on_conflict: game_id, side, batting_order).

Lineup availability:
  Lineups are typically posted ~60-90 min before first pitch.  When not yet
  confirmed the schedule response has an empty homePlayers/awayPlayers array —
  those games are skipped without error.
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

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _norm(name):
    n = (name or "").lower().strip()
    n = n.replace(".", " ")
    return re.sub(r"\s+", " ", n).strip()


def _safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _fetch_schedule(date_str):
    r = requests.get(
        f"{MLB_API_BASE}/schedule",
        params={"sportId": 1, "date": date_str, "hydrate": "lineups,team"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _fetch_hitting_stats(player_id, season):
    r = requests.get(
        f"{MLB_API_BASE}/people/{player_id}/stats",
        params={"stats": "season", "season": season, "group": "hitting"},
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
    sb_lookup = {
        (_norm(g["home_team_name"]), _norm(g["away_team_name"]), g["game_date"]): g["id"]
        for g in sb_games
    }

    saved = matched = skipped_no_lineup = 0

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

                lineups = game.get("lineups") or {}
                home_players = lineups.get("homePlayers") or []
                away_players = lineups.get("awayPlayers") or []

                if not home_players and not away_players:
                    skipped_no_lineup += 1
                    continue

                for side, players, team_name in [
                    ("home", home_players, home_name),
                    ("away", away_players, away_name),
                ]:
                    # battingOrder from MLB API is encoded as int × 100
                    batters = sorted(players, key=lambda p: int(p.get("battingOrder") or 0))

                    for slot_raw in batters:
                        raw_order = int(slot_raw.get("battingOrder") or 0)
                        order = raw_order // 100 if raw_order >= 100 else raw_order
                        if order < 1 or order > 9:
                            continue

                        person = slot_raw.get("person") or {}
                        player_id = person.get("id")
                        player_name = person.get("fullName", "Unknown")

                        try:
                            stats = _fetch_hitting_stats(player_id, season)
                            time.sleep(0.05)
                        except Exception as e:
                            print(f"  {team_name} #{order} {player_name}: stats failed: {e}")
                            stats = {}

                        gp = _safe_int(stats.get("gamesPlayed"))
                        hits = _safe_int(stats.get("hits"))
                        runs = _safe_int(stats.get("runs"))
                        rbi = _safe_int(stats.get("rbi"))
                        at_bats = _safe_int(stats.get("atBats"))

                        avg_hrr = round((hits + runs + rbi) / gp, 3) if gp > 0 else None

                        row = {
                            "game_id": game_id,
                            "game_date": date_str,
                            "side": side,
                            "team_name": team_name,
                            "batting_order": order,
                            "player_mlb_id": player_id,
                            "player_name": player_name,
                            "season": season,
                            "games_played": gp,
                            "at_bats": at_bats,
                            "hits": hits,
                            "runs": runs,
                            "rbi": rbi,
                            "avg_hrr_per_game": avg_hrr,
                            "raw_stats": stats or {},
                            "synced_at": datetime.now(ZoneInfo("UTC")).isoformat(),
                        }
                        supabase.table("mlb_lineups").upsert(
                            row, on_conflict="game_id,side,batting_order"
                        ).execute()
                        saved += 1

    print(
        f"\n✅ MLB lineups synced: {saved} batters | "
        f"{matched} games matched | {skipped_no_lineup} pending lineup"
    )


if __name__ == "__main__":
    main()
