from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    features = (
        supabase.table("soccer_match_features")
        .select("*")
        .limit(5000)
        .execute()
        .data
    )

    fallbacks = (
        supabase.table("soccer_team_profile_fallbacks")
        .select("*")
        .execute()
        .data
    )

    fallback_map = {row["team_name"]: row for row in fallbacks}

    updated = 0

    for row in features:
        home = row["home_team_name"]
        away = row["away_team_name"]

        home_fb = fallback_map.get(home)
        away_fb = fallback_map.get(away)

        update = {}

        if not row.get("home_style_label") and home_fb:
            update["home_style_label"] = home_fb["fallback_style_label"]
            update["home_adjusted_attack_index"] = home_fb["fallback_attack_index"]
            update["home_adjusted_defense_index"] = home_fb["fallback_defense_index"]
            update["home_high_card_risk"] = home_fb["fallback_cards_index"] >= 65
            update["home_high_corner_team"] = home_fb["fallback_corners_index"] >= 85

        if not row.get("away_style_label") and away_fb:
            update["away_style_label"] = away_fb["fallback_style_label"]
            update["away_adjusted_attack_index"] = away_fb["fallback_attack_index"]
            update["away_adjusted_defense_index"] = away_fb["fallback_defense_index"]
            update["away_high_card_risk"] = away_fb["fallback_cards_index"] >= 65
            update["away_high_corner_team"] = away_fb["fallback_corners_index"] >= 85

        if update:
            supabase.table("soccer_match_features").update(update).eq(
                "game_id",
                row["game_id"],
            ).execute()

            updated += 1

    print(f"✅ Profile fallbacks applied to matches: {updated}")


if __name__ == "__main__":
    main()