from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_match_features")
    .select("*")
    .order("data_quality_score", desc=True)
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
        "| Edge:",
        row["model_edge"],
        "| SOS:",
        row.get("opponent_strength_of_schedule"),
        "| Styles:",
        row.get("home_style_label"),
        "/",
        row.get("away_style_label"),
        "| LeagueGoals:",
        row.get("league_avg_goals"),
        "| Rest:",
        row.get("home_days_rest"),
        "-",
        row.get("away_days_rest"),
        "| Weather:",
        row.get("temperature_c"),
        "C",
        row.get("wind_kph"),
        "kph",
        "| Premium:",
        row["allowed_for_premium"],
    )
    