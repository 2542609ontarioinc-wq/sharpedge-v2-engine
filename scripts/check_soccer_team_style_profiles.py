from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_team_style_profiles")
    .select("*")
    .order("attack_index", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["team_name"],
        "|",
        row["style_label"],
        "| Poss:",
        row["possession_style"],
        "| Press:",
        row["high_press_style"],
        "| Direct:",
        row["direct_style"],
        "| Corner:",
        row["high_corner_team"],
        "| Cards:",
        row["high_card_risk"],
    )