from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_team_advanced_rolling_features")
    .select("*")
    .order("attack_index", desc=True)
    .limit(30)
    .execute()
    .data
)

print(f"Advanced rolling rows shown: {len(rows)}")

for row in rows:
    print(
        row["team_name"],
        "| matches:",
        row["matches_used"],
        "| wGF:",
        row["weighted_goals_for"],
        "| wGA:",
        row["weighted_goals_against"],
        "| wShots:",
        row["weighted_shots_total"],
        "| wSOG:",
        row["weighted_shots_on_goal"],
        "| homeGF:",
        row["home_goals_for"],
        "| awayGF:",
        row["away_goals_for"],
        "| Attack:",
        row["attack_index"],
        "| Defense:",
        row["defense_index"],
        "| Cards:",
        row["cards_index"],
        "| Corners:",
        row["corners_index"],
    )
    