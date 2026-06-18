from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_corners_predictions")
    .select("*")
    .order("created_at", desc=True)
    .limit(20)
    .execute()
    .data
)

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Exp corners:",
        row["expected_corners"],
        "| O7.5:",
        row["over_75_probability"],
        "| O8.5:",
        row["over_85_probability"],
        "| O9.5:",
        row["over_95_probability"],
        "| Pick:",
        row["corners_pick"],
        "| Conf:",
        row["confidence"],
    )
    