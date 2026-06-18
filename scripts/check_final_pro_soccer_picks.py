from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("final_pro_soccer_picks")
    .select("*")
    .order("final_value_rating", desc=True)
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
        "| Tier:",
        row["final_tier"],
        "| Rating:",
        row["final_value_rating"],
        "| Safe:",
        row["final_allowed"],
    )
    print("  ", row["explanation"])
    