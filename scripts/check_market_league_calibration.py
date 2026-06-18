from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_market_league_calibration")
    .select("*")
    .order("created_at", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["market"],
        "| League:",
        row["league_key"],
        "| Bucket:",
        row["confidence_bucket"],
        "| Total:",
        row["total_predictions"],
        "| W-L:",
        row["wins"],
        "-",
        row["losses"],
        "| Actual:",
        row["actual_win_rate"],
    )
    