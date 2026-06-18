from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_model_safety_flags")
    .select("*")
    .order("safety_score", desc=False)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Safety:",
        row["safety_score"],
        "| Cap:",
        row["value_cap"],
        "| Allowed:",
        row["final_allowed"],
        "| Notes:",
        row["safety_notes"],
    )
    