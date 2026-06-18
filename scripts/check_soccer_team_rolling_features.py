from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_team_rolling_features")
    .select("*")
    .order("attacking_score", desc=True)
    .limit(30)
    .execute()
    .data
)

print(f"Rolling feature rows shown: {len(rows)}")

for row in rows:
    print(
        row["team_name"],
        "| matches:",
        row["matches_used"],
        "| GF:",
        row["avg_goals_for"],
        "| GA:",
        row["avg_goals_against"],
        "| Shots:",
        row["avg_shots_total"],
        "| SOG:",
        row["avg_shots_on_goal"],
        "| Corners:",
        row["avg_corners"],
        "| Fouls:",
        row["avg_fouls"],
        "| YC:",
        row["avg_yellow_cards"],
        "| Attack:",
        row["attacking_score"],
        "| Defense:",
        row["defensive_score"],
        "| Discipline:",
        row["discipline_risk_score"],
        "| CornerPressure:",
        row["corner_pressure_score"],
    )
    