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

print(f"Feature rows shown: {len(rows)}")

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Pick:",
        row["best_pick"],
        "| Market:",
        row["best_market"],
        "| Conf:",
        row["best_confidence"],
        "| Edge:",
        row["model_edge"],
        "| Quality:",
        row["data_quality_score"],
        "| Premium:",
        row["allowed_for_premium"],
    )
    