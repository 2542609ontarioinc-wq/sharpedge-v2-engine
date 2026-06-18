from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_goal_predictions")
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
        "| xG:",
        row["expected_home_goals"],
        "-",
        row["expected_away_goals"],
        "| Total:",
        row["expected_total_goals"],
        "| O2.5:",
        row["over_25_probability"],
        "| BTTS:",
        row["btts_yes_probability"],
    )
    