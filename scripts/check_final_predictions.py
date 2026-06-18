from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("final_soccer_predictions")
    .select("*")
    .order("ensemble_score", desc=True)
    .limit(20)
    .execute()
    .data
)

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| BEST:",
        row["best_pick"],
        "| Market:",
        row["market"],
        "| Conf:",
        row["confidence"],
        "| Rating:",
        row["value_rating"],
        "| Score:",
        row["ensemble_score"],
    )
    