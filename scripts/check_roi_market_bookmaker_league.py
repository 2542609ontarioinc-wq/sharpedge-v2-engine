from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_roi_market_bookmaker_league")
    .select("*")
    .order("created_at", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["market"],
        "| Book:",
        row["bookmaker"],
        "| League:",
        row["league_key"],
        "| Bets:",
        row["total_bets"],
        "| ROI:",
        row["roi_percentage"],
    )
    