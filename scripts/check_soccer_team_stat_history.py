from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_team_stat_history")
    .select("*")
    .order("game_date", desc=True)
    .limit(30)
    .execute()
    .data
)

print(f"Team stat history rows shown: {len(rows)}")

for row in rows:
    print(
        row["game_date"],
        "|",
        row["team_name"],
        "| GF:",
        row["goals_for"],
        "| GA:",
        row["goals_against"],
        "| Shots:",
        row["shots_total"],
        "| SOG:",
        row["shots_on_goal"],
        "| Poss:",
        row["possession_percent"],
        "| Corners:",
        row["corners"],
        "| Fouls:",
        row["fouls"],
        "| YC:",
        row["yellow_cards"],
    )
    