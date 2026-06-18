from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_btts_prediction_versions")
    .select("*")
    .eq("model_version", "btts_ml_v2")
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
        "| BTTS Yes:",
        row["btts_yes_probability"],
        "| BTTS No:",
        row["btts_no_probability"],
        "| Pick:",
        row["predicted_btts"],
        "| Confidence:",
        row["confidence_score"],
    )
    