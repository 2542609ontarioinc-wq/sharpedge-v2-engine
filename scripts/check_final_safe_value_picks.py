from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

values = (
    supabase.table("soccer_market_value")
    .select("*")
    .order("value_rating", desc=True)
    .limit(30)
    .execute()
    .data
)

flags = (
    supabase.table("soccer_model_safety_flags")
    .select("*")
    .execute()
    .data
)

features = (
    supabase.table("soccer_match_features")
    .select("*")
    .execute()
    .data
)

flag_map = {row["game_id"]: row for row in flags}
feature_map = {row["game_id"]: row for row in features}

for row in values:
    game_id = row["game_id"]

    flag = flag_map.get(game_id, {})
    feature = feature_map.get(game_id, {})

    print(
        feature.get("home_team_name"),
        "vs",
        feature.get("away_team_name"),
        "| Pick:",
        feature.get("best_pick"),
        "| Market:",
        row.get("market"),
        "| Book:",
        row.get("bookmaker"),
        "| Edge:",
        row.get("edge"),
        "| EV:",
        row.get("expected_value"),
        "| Kelly:",
        row.get("kelly_fraction"),
        "| Value:",
        row.get("value_rating"),
        "| Safe:",
        flag.get("final_allowed"),
        "| Notes:",
        flag.get("safety_notes"),
    )