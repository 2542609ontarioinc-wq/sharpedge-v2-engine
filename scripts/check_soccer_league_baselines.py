from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_league_baselines")
    .select("*")
    .order("matches_used", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["league_name"],
        "| matches:",
        row["matches_used"],
        "| goals:",
        row["avg_goals"],
        "| shots:",
        row["avg_shots"],
        "| corners:",
        row["avg_corners"],
        "| fouls:",
        row["avg_fouls"],
        "| YC:",
        row["avg_yellow_cards"],
        "| BTTS:",
        row["btts_rate"],
        "| O2.5:",
        row["over_25_rate"],
    )