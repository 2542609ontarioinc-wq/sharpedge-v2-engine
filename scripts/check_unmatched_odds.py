from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_odds")
    .select("home_team_name, away_team_name, market, selection")
    .is_("game_id", "null")
    .limit(50)
    .execute()
    .data
)

print(f"Unmatched odds rows shown: {len(rows)}")

seen = set()

for row in rows:
    key = (row["home_team_name"], row["away_team_name"])

    if key in seen:
        continue

    seen.add(key)

    print(row["home_team_name"], "vs", row["away_team_name"])