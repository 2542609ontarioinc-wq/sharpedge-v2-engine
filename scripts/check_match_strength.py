from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_match_strength")
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
        "| home:",
        row["home_form_score"],
        "| away:",
        row["away_form_score"],
        "| diff:",
        row["form_difference"],
        "| edge:",
        row["predicted_edge"],
    )
    