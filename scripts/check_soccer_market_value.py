from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_market_value")
    .select("*")
    .order("value_rating", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    game = (
        supabase.table("soccer_match_features")
        .select("home_team_name, away_team_name, best_pick")
        .eq("game_id", row["game_id"])
        .limit(1)
        .execute()
        .data
    )

    label = "Unknown"
    pick = ""

    if game:
        label = f'{game[0]["home_team_name"]} vs {game[0]["away_team_name"]}'
        pick = game[0]["best_pick"]

    print(
        label,
        "| Pick:",
        pick,
        "| Market:",
        row["market"],
        "| Book:",
        row["bookmaker"],
        "| Model:",
        row["model_probability"],
        "| Implied:",
        row["implied_probability"],
        "| Edge:",
        row["edge"],
        "| EV:",
        row["expected_value"],
        "| Kelly:",
        row["kelly_fraction"],
        "| Rating:",
        row["value_rating"],
    )