from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.apisports_client import APISportsClient

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
client = APISportsClient()


def sync_completed_games_for_priority_leagues(season=2026):
    leagues = (
        supabase.table("priority_leagues")
        .select("league_id, league_name")
        .eq("sport_key", "soccer")
        .eq("enabled", True)
        .execute()
        .data
    )

    saved = 0

    for league in leagues:
        league_id = league["league_id"]
        print(f"Syncing league {league_id} - {league['league_name']}")

        data = client._get(
            f"{client.football_base_url}/fixtures",
            params={
                "league": league_id,
                "season": season,
                "status": "FT",
            },
        )

        fixtures = data.get("response", [])

        for item in fixtures:
            fixture = item.get("fixture", {})
            league_data = item.get("league", {})
            teams = item.get("teams", {})
            goals = item.get("goals", {})

            home = teams.get("home", {})
            away = teams.get("away", {})

            home_score = goals.get("home")
            away_score = goals.get("away")

            if home_score is None or away_score is None:
                continue

            if home_score > away_score:
                result = "home"
            elif away_score > home_score:
                result = "away"
            else:
                result = "draw"

            row = {
                "fixture_id": str(fixture.get("id")),
                "league_id": str(league_data.get("id")),
                "league_name": league_data.get("name"),
                "country": league_data.get("country"),
                "season": str(league_data.get("season")),
                "game_date": fixture.get("date", "")[:10],
                "home_team_id": str(home.get("id")),
                "away_team_id": str(away.get("id")),
                "home_team_name": home.get("name"),
                "away_team_name": away.get("name"),
                "home_score": home_score,
                "away_score": away_score,
                "result": result,
                "total_goals": home_score + away_score,
                "btts": home_score > 0 and away_score > 0,
                "raw_json": item,
            }

            supabase.table("soccer_historical_results").upsert(
                row,
                on_conflict="fixture_id",
            ).execute()

            saved += 1

    print(f"✅ Historical results synced: {saved}")


if __name__ == "__main__":
    sync_completed_games_for_priority_leagues()
    