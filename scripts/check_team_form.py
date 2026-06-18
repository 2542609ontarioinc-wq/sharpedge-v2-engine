from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_form_features")
    .select("*")
    .order("created_at", desc=True)
    .limit(20)
    .execute()
).data

for row in rows:
    print(
        row["team_name"],
        "| matches:",
        row["matches_checked"],
        "| W-D-L:",
        row["wins"],
        row["draws"],
        row["losses"],
        "| GF:",
        row["goals_for"],
        "| GA:",
        row["goals_against"],
        "| form:",
        row["form_score"],
    )
    