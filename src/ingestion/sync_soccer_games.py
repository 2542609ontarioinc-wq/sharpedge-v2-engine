from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.apisports_client import APISportsClient


TORONTO_TZ = ZoneInfo("America/Toronto")


def parse_datetime_to_toronto(date_value):
    if not date_value:
        return None

    dt = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
    return dt.astimezone(TORONTO_TZ)


def upsert_team(supabase, team, sport_key="soccer"):
    team_data = {
        "sport_key": sport_key,
        "external_team_id": str(team.get("id")),
        "name": team.get("name"),
        "logo_url": team.get("logo"),
        "metadata": team,
    }

    response = (
        supabase.table("teams")
        .upsert(team_data, on_conflict="sport_key,external_team_id")
        .execute()
    )

    return response.data[0]["id"] if response.data else None


def upsert_venue(supabase, fixture, sport_key="soccer"):
    venue = fixture.get("venue") or {}

    if not venue.get("id") and not venue.get("name"):
        return None

    venue_data = {
        "sport_key": sport_key,
        "external_venue_id": str(venue.get("id")) if venue.get("id") else None,
        "name": venue.get("name") or "Unknown Venue",
        "city": venue.get("city"),
        "metadata": venue,
    }

    response = (
        supabase.table("venues")
        .upsert(venue_data, on_conflict="sport_key,external_venue_id")
        .execute()
    )

    return response.data[0]["id"] if response.data else None


def sync_soccer_games_for_date(date_str):
    client = APISportsClient()
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    print(f"Syncing soccer games for API date: {date_str}")

    data = client.get_soccer_fixtures_by_date(date_str)
    fixtures = data.get("response", [])

    print(f"Fixtures found: {len(fixtures)}")

    saved = 0

    for item in fixtures:
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})

        home = teams.get("home", {})
        away = teams.get("away", {})

        fixture_utc_date = fixture.get("date")
        start_dt_toronto = parse_datetime_to_toronto(fixture_utc_date)

        if not start_dt_toronto:
            continue

        actual_game_date_toronto = start_dt_toronto.strftime("%Y-%m-%d")

        home_team_id = upsert_team(supabase, home)
        away_team_id = upsert_team(supabase, away)
        venue_id = upsert_venue(supabase, fixture)

        game_data = {
            "sport_key": "soccer",
            "league_key": str(league.get("id")) if league.get("id") else None,
            "external_game_id": str(fixture.get("id")),
            "season": str(league.get("season")) if league.get("season") else None,
            "game_date": actual_game_date_toronto,
            "start_time_utc": fixture_utc_date,
            "start_time_toronto": start_dt_toronto.isoformat(),
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_team_name": home.get("name"),
            "away_team_name": away.get("name"),
            "venue_id": venue_id,
            "status": (fixture.get("status") or {}).get("short"),
            "period": (fixture.get("status") or {}).get("long"),
            "home_score": goals.get("home") if goals.get("home") is not None else 0,
            "away_score": goals.get("away") if goals.get("away") is not None else 0,
            "source": "api-sports",
            "raw_json": item,
        }

        supabase.table("games").upsert(
            game_data,
            on_conflict="sport_key,external_game_id",
        ).execute()

        saved += 1

    print(f"✅ Soccer games saved: {saved}")


if __name__ == "__main__":
    toronto_today = datetime.now(TORONTO_TZ).strftime("%Y-%m-%d")
    sync_soccer_games_for_date(toronto_today)