from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_rest_travel_features")
    .select("*")
    .order("congestion_score", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| rest:",
        row["home_days_rest"],
        "-",
        row["away_days_rest"],
        "| last7:",
        row["home_matches_last_7"],
        "-",
        row["away_matches_last_7"],
        "| last14:",
        row["home_matches_last_14"],
        "-",
        row["away_matches_last_14"],
        "| RestAdv:",
        row["rest_advantage"],
        "| Congestion:",
        row["congestion_score"],
    )