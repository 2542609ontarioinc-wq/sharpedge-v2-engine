from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_team_profile_fallbacks")
    .select("*")
    .order("fallback_attack_index", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["team_name"],
        "| matches:",
        row["matches_used"],
        "| Attack:",
        row["fallback_attack_index"],
        "| Defense:",
        row["fallback_defense_index"],
        "| Cards:",
        row["fallback_cards_index"],
        "| Corners:",
        row["fallback_corners_index"],
        "| Style:",
        row["fallback_style_label"],
    )
    