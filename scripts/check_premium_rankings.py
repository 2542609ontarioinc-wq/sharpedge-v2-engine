from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_premium_rankings")
    .select("*")
    .order("rank")
    .limit(20)
    .execute()
    .data
)

for row in rows:
    print(
        "#",
        row["rank"],
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Pick:",
        row["best_pick"],
        "| Market:",
        row["market"],
        "| Conf:",
        row["confidence"],
        "| Score:",
        row["ensemble_score"],
        "| Tier:",
        row["tier"],
    )
    