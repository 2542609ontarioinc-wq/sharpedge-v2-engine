"""
Sync MLB games (upcoming + recent finished) from API-Sports baseball into the
shared `games` table with sport_key='baseball_mlb'.

Syncs today ±3 days for upcoming picks, plus the past HISTORY_DAYS days for
backtest data.  Status mapping mirrors the soccer ingestion pattern.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.apisports_client import APISportsClient

TORONTO = ZoneInfo("America/Toronto")
MLB_LEAGUE_ID = 1
SPORT_KEY = "baseball_mlb"
HISTORY_DAYS = 60


def _ts_to_toronto(timestamp_int):
    if not timestamp_int:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp_int), tz=ZoneInfo("UTC")).astimezone(TORONTO)
    except Exception:
        return None


def _upsert_team(supabase, team):
    if not team or not team.get("id"):
        return None
    row = {
        "sport_key": SPORT_KEY,
        "external_team_id": str(team["id"]),
        "name": team.get("name") or "Unknown",
        "logo_url": team.get("logo"),
        "metadata": team,
    }
    res = supabase.table("teams").upsert(row, on_conflict="sport_key,external_team_id").execute()
    return res.data[0]["id"] if res.data else None


def _sync_date(client, supabase, date_str):
    season = int(date_str[:4])
    data = client.get_baseball_games_by_league_date(date_str, league_id=MLB_LEAGUE_ID, season=season)
    games = data.get("response", [])
    saved = 0
    for item in games:
        teams = item.get("teams", {})
        scores = item.get("scores", {})
        status = item.get("status", {})
        league = item.get("league", {})

        home = teams.get("home", {})
        away = teams.get("away", {})

        dt_toronto = _ts_to_toronto(item.get("timestamp"))
        game_date = dt_toronto.strftime("%Y-%m-%d") if dt_toronto else date_str

        home_id = _upsert_team(supabase, home)
        away_id = _upsert_team(supabase, away)

        home_score = (scores.get("home") or {}).get("total")
        away_score = (scores.get("away") or {}).get("total")

        row = {
            "sport_key": SPORT_KEY,
            "league_key": str(league.get("id")) if league.get("id") else None,
            "external_game_id": str(item["id"]),
            "season": str(league.get("season")) if league.get("season") else None,
            "game_date": game_date,
            "start_time_utc": datetime.fromtimestamp(
                int(item["timestamp"]), tz=ZoneInfo("UTC")
            ).isoformat() if item.get("timestamp") else None,
            "start_time_toronto": dt_toronto.isoformat() if dt_toronto else None,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_team_name": home.get("name") or "Unknown",
            "away_team_name": away.get("name") or "Unknown",
            "status": status.get("short"),
            "period": status.get("long"),
            "home_score": home_score if home_score is not None else 0,
            "away_score": away_score if away_score is not None else 0,
            "source": "api-sports-baseball",
            "raw_json": item,
            "last_synced_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        }
        supabase.table("games").upsert(row, on_conflict="sport_key,external_game_id").execute()
        saved += 1
    return saved, len(games)


def main():
    client = APISportsClient()
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    today = datetime.now(TORONTO).date()
    dates = set()

    # Upcoming: today + next 3 days
    for delta in range(4):
        dates.add((today + timedelta(days=delta)).isoformat())

    # Historical: past HISTORY_DAYS days for backtest data
    for delta in range(1, HISTORY_DAYS + 1):
        dates.add((today - timedelta(days=delta)).isoformat())

    total_saved = total_found = 0
    for date_str in sorted(dates):
        saved, found = _sync_date(client, supabase, date_str)
        total_saved += saved
        total_found += found
        if found:
            print(f"  {date_str}: {found} games found, {saved} upserted")

    print(f"\n✅ MLB games synced: {total_saved} rows across {len(dates)} dates")


if __name__ == "__main__":
    main()
