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

    priors = (
        supabase.table("soccer_team_global_priors")
        .select("*")
        .execute()
        .data
    )

    prior_map = {row["team_name"]: row for row in priors}

    updated = 0

    for row in features:
        home = row["home_team_name"]
        away = row["away_team_name"]

        home_prior = prior_map.get(home)
        away_prior = prior_map.get(away)

        update = {}

        if not row.get("home_style_label") and home_prior:
            update["home_style_label"] = home_prior["prior_style_label"]
            update["home_adjusted_attack_index"] = home_prior["prior_attack_index"]
            update["home_adjusted_defense_index"] = home_prior["prior_defense_index"]
            update["home_high_card_risk"] = home_prior["prior_cards_index"] >= 65
            update["home_high_corner_team"] = home_prior["prior_corners_index"] >= 80

        if not row.get("away_style_label") and away_prior:
            update["away_style_label"] = away_prior["prior_style_label"]
            update["away_adjusted_attack_index"] = away_prior["prior_attack_index"]
            update["away_adjusted_defense_index"] = away_prior["prior_defense_index"]
            update["away_high_card_risk"] = away_prior["prior_cards_index"] >= 65
            update["away_high_corner_team"] = away_prior["prior_corners_index"] >= 80

        if update:
            supabase.table("soccer_match_features").update(update).eq(
                "game_id",
                row["game_id"],
            ).execute()

            updated += 1

    print(f"✅ Global priors applied to matches: {updated}")


if __name__ == "__main__":
    main()