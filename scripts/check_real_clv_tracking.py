from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_clv_tracking")
    .select("*")
    .order("created_at", desc=True)
    .limit(20)
    .execute()
    .data
)

for row in rows:
    print(
        row["market"],
        "| Open:",
        row["opening_odds"],
        "| Close:",
        row["closing_odds"],
        "| Diff:",
        row["clv_difference"],
        "| Beat:",
        row["beat_closing_line"],
    )
    