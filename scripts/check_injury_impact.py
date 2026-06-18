from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_injury_impact")
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
        "| Home injuries:",
        row["home_injuries"],
        "| Away injuries:",
        row["away_injuries"],
        "| Impact:",
        row["injury_impact_score"],
        "| Available:",
        row["injury_available"],
    )
    