from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_match_features")
    .select("*")
    .order("data_quality_score", desc=True)
    .limit(40)
    .execute()
    .data
)

missing = 0

for row in rows:
    if not row.get("home_style_label") or not row.get("away_style_label"):
        missing += 1

    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Styles:",
        row.get("home_style_label"),
        "/",
        row.get("away_style_label"),
        "| Attack:",
        row.get("home_adjusted_attack_index"),
        "-",
        row.get("away_adjusted_attack_index"),
        "| Defense:",
        row.get("home_adjusted_defense_index"),
        "-",
        row.get("away_adjusted_defense_index"),
        "| Premium:",
        row.get("allowed_for_premium"),
    )

print("Missing style rows shown:", missing)