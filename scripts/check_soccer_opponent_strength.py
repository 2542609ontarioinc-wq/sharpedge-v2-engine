from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_opponent_strength")
    .select("*")
    .order("strength_of_schedule", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["team_name"],
        "| matches:",
        row["matches_used"],
        "| OppAttack:",
        row["avg_opponent_attack"],
        "| OppDefense:",
        row["avg_opponent_defense"],
        "| SOS:",
        row["strength_of_schedule"],
        "| AdjAttack:",
        row["adjusted_attack_index"],
        "| AdjDefense:",
        row["adjusted_defense_index"],
    )