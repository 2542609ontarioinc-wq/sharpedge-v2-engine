from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("final_soccer_predictions")
    .select("*")
    .order("ensemble_score", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Pick:",
        row["best_pick"],
        "| Book:",
        row.get("bookmaker"),
        "| Odds:",
        row.get("odds_decimal"),
        "| Market:",
        row.get("market_implied_probability"),
        "| Model:",
        row.get("confidence"),
        "| Edge:",
        row.get("model_edge"),
    )
    