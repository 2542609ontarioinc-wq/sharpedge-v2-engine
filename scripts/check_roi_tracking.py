from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_roi_tracking")
    .select("*")
    .order("created_at", desc=True)
    .limit(10)
    .execute()
    .data
)

for row in rows:
    print(
        row["market"],
        "| Bets:",
        row["total_bets"],
        "| W-L:",
        row["wins"],
        "-",
        row["losses"],
        "| Profit:",
        row["profit_units"],
        "u",
        "| ROI:",
        row["roi_percentage"],
        "%",
    )
    