from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_prediction_results")
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
        "| Home:",
        row["home_win_probability"],
        "| Draw:",
        row["draw_probability"],
        "| Away:",
        row["away_win_probability"],
        "| Pick:",
        row["predicted_winner"],
        "| Confidence:",
        row["confidence_score"],
    )