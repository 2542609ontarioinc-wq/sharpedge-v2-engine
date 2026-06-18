from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.apisports_client import APISportsClient

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
client = APISportsClient()


def stat_value(stats, name):
    for item in stats:
        if item.get("type") == name:
            value = item.get("value")

            if value is None:
                return 0

            if isinstance(value, int):
                return value

            if isinstance(value, str):
                cleaned = value.replace("%", "").strip()
                if cleaned.isdigit():
                    return int(cleaned)

    return 0


def main():
    results = (
        supabase.table("soccer_historical_results")
        .select("*")
        .limit(500)
        .execute()
        .data
    )

    saved = 0

    for result in results:
        fixture_id = result["fixture_id"]

        stats_data = client.get_soccer_fixture_statistics(fixture_id)
        stats_response = stats_data.get("response", [])

        if not stats_response:
            continue

        for team_stats in stats_response:
            team = team_stats.get("team", {})
            stats = team_stats.get("statistics", [])

            team_id = str(team.get("id"))
            team_name = team.get("name")

            is_home = team_id == str(result["home_team_id"])

            if is_home:
                goals_for = result["home_score"]
                goals_against = result["away_score"]
                opponent_id = result["away_team_id"]
                opponent_name = result["away_team_name"]
            else:
                goals_for = result["away_score"]
                goals_against = result["home_score"]
                opponent_id = result["home_team_id"]
                opponent_name = result["home_team_name"]

            row = {
                "fixture_id": fixture_id,
                "league_id": result["league_id"],
                "league_name": result["league_name"],
                "season": result["season"],
                "game_date": result["game_date"],

                "team_id": team_id,
                "team_name": team_name,

                "opponent_team_id": opponent_id,
                "opponent_team_name": opponent_name,

                "is_home": is_home,

                "goals_for": goals_for,
                "goals_against": goals_against,

                "shots_total": stat_value(stats, "Total Shots"),
                "shots_on_goal": stat_value(stats, "Shots on Goal"),
                "possession_percent": stat_value(stats, "Ball Possession"),

                "corners": stat_value(stats, "Corner Kicks"),
                "fouls": stat_value(stats, "Fouls"),
                "yellow_cards": stat_value(stats, "Yellow Cards"),
                "red_cards": stat_value(stats, "Red Cards"),

                "raw_json": team_stats,
            }

            supabase.table("soccer_team_stat_history").upsert(
                row,
                on_conflict="fixture_id,team_id",
            ).execute()

            saved += 1

    print(f"✅ Soccer team stat history rows upserted: {saved}")


if __name__ == "__main__":
    main()
    