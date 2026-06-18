from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_market_snapshots")
    .select("*")
    .order("snapshot_time", desc=True)
    .limit(30)
    .execute()
    .data
)

print(f"Market snapshots shown: {len(rows)}")

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "|",
        row["market"],
        "|",
        row["selection"],
        "|",
        row["bookmaker"],
        "| odds:",
        row["odds_decimal"],
        "| imp:",
        row["implied_probability"],
    )
    