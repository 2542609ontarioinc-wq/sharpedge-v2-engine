from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_lineup_impact")
    .select("*")
    .order("created_at", desc=True)
    .limit(20)
    .execute()
    .data
)

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Home XI:",
        row["home_lineup_count"],
        "| Away XI:",
        row["away_lineup_count"],
        "| Available:",
        row["lineup_available"],
        "| Impact:",
        row["lineup_impact_score"],
    )
    