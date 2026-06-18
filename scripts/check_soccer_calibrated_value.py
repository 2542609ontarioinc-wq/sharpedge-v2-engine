from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_calibrated_value")
    .select("*")
    .order("final_value_rating", desc=True)
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
        row["pick"],
        "| Market:",
        row["market"],
        "| Raw:",
        row["raw_value_rating"],
        "| Safety:",
        row["safety_score"],
        "| Matchup:",
        row["matchup_score"],
        "| Final:",
        row["final_value_rating"],
        "| Tier:",
        row["final_tier"],
        "| Allowed:",
        row["final_allowed"],
        "| Notes:",
        row["notes"],
    )