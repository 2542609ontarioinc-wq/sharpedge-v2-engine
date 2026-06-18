from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_referee_history")
    .select("*")
    .order("card_strictness_score", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["referee_name"],
        "| matches:",
        row["matches_used"],
        "| YC:",
        row["avg_yellow_cards"],
        "| RC:",
        row["avg_red_cards"],
        "| Fouls:",
        row["avg_fouls"],
        "| Corners:",
        row["avg_corners"],
        "| Goals:",
        row["avg_goals"],
        "| Strict:",
        row["card_strictness_score"],
        "| Flow:",
        row["game_flow_score"],
    )