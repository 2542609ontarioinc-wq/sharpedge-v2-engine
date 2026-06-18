from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_api_ready_view")
    .select("*")
    .order("final_value_rating", desc=True)
    .execute()
    .data
)

print(f"Rows: {len(rows)}")

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Pick:",
        row["pick"],
        "| Rating:",
        row["final_value_rating"],
        "| Tier:",
        row["final_tier"],
        "| Conf:",
        row["best_confidence"],
        "| Edge:",
        row["model_edge"],
        "| Weather:",
        row["temperature_c"],
        "C",
        row["wind_kph"],
        "kph",
        "| Styles:",
        row["home_style_label"],
        "/",
        row["away_style_label"],
    )
    