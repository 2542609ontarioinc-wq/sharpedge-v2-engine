from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_backtest_reports")
    .select("*")
    .order("created_at", desc=True)
    .limit(5)
    .execute()
    .data
)

for row in rows:
    print("Report:", row["report_name"])
    print("Total:", row["total_games"])
    print("Winner:", row["winner_wins"], "-", row["winner_losses"], "|", row["winner_accuracy"], "%")
    print("Over 2.5:", row["over_25_wins"], "-", row["over_25_losses"], "|", row["over_25_accuracy"], "%")
    print("BTTS:", row["btts_wins"], "-", row["btts_losses"], "|", row["btts_accuracy"], "%")
    print("-----")
    