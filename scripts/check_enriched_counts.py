from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

result = (
    supabase.table("games")
    .select("home_team_name,away_team_name,raw_json")
    .eq("sport_key", "soccer")
    .eq("league_key", "1")
    .limit(10)
    .execute()
)

for game in result.data:
    raw = game.get("raw_json") or {}
    enriched = raw.get("enriched_details") or {}

    print(game["home_team_name"], "vs", game["away_team_name"])

    for key in ["statistics", "events", "lineups", "players", "injuries"]:
        data = enriched.get(key) or {}
        response = data.get("response", []) if isinstance(data, dict) else []
        print(key, len(response))

    print("-----")
    