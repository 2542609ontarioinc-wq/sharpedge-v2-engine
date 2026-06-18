from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_cards_predictions")
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
        "| Exp cards:",
        row["expected_cards"],
        "| O3.5:",
        row["over_35_probability"],
        "| O4.5:",
        row["over_45_probability"],
        "| Pick:",
        row["cards_pick"],
        "| Conf:",
        row["confidence"],
    )
    