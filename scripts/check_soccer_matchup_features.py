from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_matchup_features")
    .select("*")
    .order("overall_matchup_score", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["home_team"],
        "vs",
        row["away_team"],
        "| AttackEdge:",
        row["attack_edge"],
        "| DefenseEdge:",
        row["defense_edge"],
        "| Corners:",
        row["corner_edge"],
        "| Cards:",
        row["card_edge"],
        "| Style:",
        row["style_matchup"],
        "| Weather:",
        row["weather_fit"],
        "| Tactical:",
        row["tactical_edge"],
        "| Overall:",
        row["overall_matchup_score"],
    )
    