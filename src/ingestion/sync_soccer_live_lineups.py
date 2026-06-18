import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY, APISPORTS_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
TORONTO = ZoneInfo("America/Toronto")

BASE_URL = "https://v3.football.api-sports.io"


def norm(s):
    return (s or "").lower().replace(".", "").replace("-", " ").strip()


def get_fixture_id(game):
    raw = game.get("raw_json") or {}
    fixture = raw.get("fixture") or {}
    return fixture.get("id")


def fetch_lineups(fixture_id):
    res = requests.get(
        f"{BASE_URL}/fixtures/lineups",
        headers={"x-apisports-key": APISPORTS_KEY},
        params={"fixture": fixture_id},
        timeout=20,
    )

    if res.status_code != 200:
        return []

    return res.json().get("response") or []


def main():
    today = datetime.now(TORONTO).date()

    games = (
        supabase.table("games")
        .select("*")
        .eq("sport_key", "soccer")
        .execute()
        .data
    )

    saved = 0
    checked = 0

    for game in games:
        raw = game.get("raw_json") or {}
        fixture = raw.get("fixture") or {}
        dt_raw = fixture.get("date")

        if not dt_raw:
            continue

        dt = datetime.fromisoformat(dt_raw.replace("Z", "+00:00")).astimezone(TORONTO)

        if dt.date() != today:
            continue

        fixture_id = get_fixture_id(game)
        if not fixture_id:
            continue

        checked += 1

        lineups = fetch_lineups(fixture_id)

        home_name = game.get("home_team_name")
        away_name = game.get("away_team_name")

        home_lineup = None
        away_lineup = None

        for lineup in lineups:
            team_name = ((lineup.get("team") or {}).get("name")) or ""

            if norm(team_name) == norm(home_name):
                home_lineup = lineup
            elif norm(team_name) == norm(away_name):
                away_lineup = lineup

        home_xi = len((home_lineup or {}).get("startXI") or [])
        away_xi = len((away_lineup or {}).get("startXI") or [])

        if home_xi == 11 and away_xi == 11:
            status = "confirmed"
        elif home_xi or away_xi:
            status = "partial"
        else:
            status = "not_available"

        out = {
            "game_id": game["id"],
            "api_fixture_id": fixture_id,
            "home_team_name": home_name,
            "away_team_name": away_name,
            "home_confirmed_xi": home_xi,
            "away_confirmed_xi": away_xi,
            "home_formation": (home_lineup or {}).get("formation"),
            "away_formation": (away_lineup or {}).get("formation"),
            "lineup_status": status,
            "raw_json": lineups,
            "updated_at": datetime.utcnow().isoformat(),
        }

        supabase.table("soccer_live_lineups").upsert(
            out,
            on_conflict="game_id",
        ).execute()

        saved += 1

        print(
            f'{home_name} vs {away_name} | Fixture {fixture_id} | '
            f'Home XI: {home_xi} | Away XI: {away_xi} | {status}'
        )

    print(f"✅ Live lineup games checked: {checked}")
    print(f"✅ Live lineup rows upserted: {saved}")


if __name__ == "__main__":
    main()
    