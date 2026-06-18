from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_odds")
    .select("*")
    .order("captured_at", desc=True)
    .limit(30)
    .execute()
    .data
)

print(f"Odds rows shown: {len(rows)}")

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
        "| dec:",
        row["odds_decimal"],
        "| imp:",
        row["implied_probability"],
    )
    