from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)

result = (
    supabase.table("games")
    .select("home_team_name,away_team_name,raw_json")
    .limit(10)
    .execute()
)

for game in result.data:
    enriched = (
        game.get("raw_json", {})
        .get("enriched_details", {})
    )

    print(
        game["home_team_name"],
        "vs",
        game["away_team_name"]
    )

    print(
        "stats:",
        "statistics" in enriched
    )

    print(
        "events:",
        "events" in enriched
    )

    print(
        "lineups:",
        "lineups" in enriched
    )

    print(
        "players:",
        "players" in enriched
    )

    print("-----")