from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.apisports_client import APISportsClient


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    client = APISportsClient()

    priority_result = (
        supabase.table("priority_leagues")
        .select("league_id")
        .eq("sport_key", "soccer")
        .eq("enabled", True)
        .execute()
    )

    priority_ids = [row["league_id"] for row in priority_result.data]

    games_result = (
        supabase.table("games")
        .select("id, external_game_id, home_team_name, away_team_name, league_key, raw_json")
        .eq("sport_key", "soccer")
        .in_("league_key", priority_ids)
        .limit(50)
        .execute()
    )

    games = games_result.data or []

    print(f"Priority games to enrich: {len(games)}")

    for game in games:
        fixture_id = game["external_game_id"]

        print(f"Enriching: {game['home_team_name']} vs {game['away_team_name']}")

        existing_raw = game.get("raw_json") or {}

        details = {
            "statistics": client.get_soccer_fixture_statistics(fixture_id),
            "events": client.get_soccer_fixture_events(fixture_id),
            "lineups": client.get_soccer_fixture_lineups(fixture_id),
            "players": client.get_soccer_fixture_players(fixture_id),
        }

        try:
            details["injuries"] = client.get_soccer_injuries_by_fixture(fixture_id)
        except Exception as e:
            details["injuries"] = {"error": str(e)}

        existing_raw["enriched_details"] = details

        supabase.table("games").update(
            {"raw_json": existing_raw}
        ).eq("id", game["id"]).execute()

    print("✅ Soccer details synced without deleting original raw_json")


if __name__ == "__main__":
    main()
    