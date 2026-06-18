from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_prediction_grades")
    .select("*")
    .order("created_at", desc=True)
    .limit(20)
    .execute()
    .data
)

print(f"Grades shown: {len(rows)}")

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| winner:",
        row["winner_grade"],
        "| O2.5:",
        row["over_25_grade"],
        "| BTTS:",
        row["btts_grade"],
    )
    