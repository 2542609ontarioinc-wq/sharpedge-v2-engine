from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_data_quality_gate")
    .select("*")
    .order("quality_score", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Score:",
        row["quality_score"],
        "| Premium:",
        row["allowed_for_premium"],
        "| Reason:",
        row["block_reason"],
    )
    