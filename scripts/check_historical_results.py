from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_historical_results")
    .select("*")
    .order("game_date", desc=True)
    .limit(20)
    .execute()
    .data
)

print(f"Historical rows shown: {len(rows)}")

for row in rows:
    print(
        row["game_date"],
        "|",
        row["league_name"],
        "|",
        row["home_team_name"],
        row["home_score"],
        "-",
        row["away_score"],
        row["away_team_name"],
        "| result:",
        row["result"],
        "| goals:",
        row["total_goals"],
        "| BTTS:",
        row["btts"],
    )
    