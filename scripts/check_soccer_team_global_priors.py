from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_team_global_priors")
    .select("*")
    .order("prior_attack_index", desc=True)
    .limit(50)
    .execute()
    .data
)

for row in rows:
    print(
        row["team_name"],
        "| Attack:",
        row["prior_attack_index"],
        "| Defense:",
        row["prior_defense_index"],
        "| Cards:",
        row["prior_cards_index"],
        "| Corners:",
        row["prior_corners_index"],
        "| Style:",
        row["prior_style_label"],
        "| Source:",
        row["source"],
    )
    