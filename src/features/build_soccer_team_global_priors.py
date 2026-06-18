from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


TIER_1 = {
    "Argentina",
    "Brazil",
    "France",
    "England",
    "Spain",
    "Germany",
    "Portugal",
    "Netherlands",
    "Belgium",
    "Uruguay",
    "Colombia",
    "Croatia",
}

TIER_2 = {
    "Switzerland",
    "Austria",
    "Denmark",
    "Sweden",
    "Norway",
    "Japan",
    "South Korea",
    "USA",
    "Mexico",
    "Morocco",
    "Senegal",
    "Ecuador",
    "Türkiye",
    "Turkey",
    "Canada",
}

PHYSICAL_TEAMS = {
    "Ghana",
    "Panama",
    "Tunisia",
    "Algeria",
    "Jordan",
    "Iraq",
    "Iran",
    "Egypt",
    "South Africa",
}

LOW_BLOCK_TEAMS = {
    "Cape Verde",
    "Cape Verde Islands",
    "Curacao",
    "Curaçao",
    "New Zealand",
    "Qatar",
    "Saudi Arabia",
    "Haiti",
}


def prior_for_team(team_name):
    if team_name in TIER_1:
        return {
            "prior_attack_index": 130,
            "prior_defense_index": 65,
            "prior_cards_index": 45,
            "prior_corners_index": 80,
            "prior_style_label": "Elite / Possession",
            "source": "tier_1_national_prior",
        }

    if team_name in TIER_2:
        return {
            "prior_attack_index": 115,
            "prior_defense_index": 58,
            "prior_cards_index": 50,
            "prior_corners_index": 70,
            "prior_style_label": "Strong / Balanced",
            "source": "tier_2_national_prior",
        }

    if team_name in PHYSICAL_TEAMS:
        return {
            "prior_attack_index": 95,
            "prior_defense_index": 52,
            "prior_cards_index": 70,
            "prior_corners_index": 58,
            "prior_style_label": "Physical / Card Risk",
            "source": "physical_team_prior",
        }

    if team_name in LOW_BLOCK_TEAMS:
        return {
            "prior_attack_index": 80,
            "prior_defense_index": 55,
            "prior_cards_index": 55,
            "prior_corners_index": 48,
            "prior_style_label": "Low Block / Defensive",
            "source": "low_block_prior",
        }

    return {
        "prior_attack_index": 100,
        "prior_defense_index": 50,
        "prior_cards_index": 50,
        "prior_corners_index": 60,
        "prior_style_label": "Balanced",
        "source": "default_global_prior",
    }


def main():
    games = (
        supabase.table("soccer_match_features")
        .select("home_team_name, away_team_name")
        .limit(5000)
        .execute()
        .data
    )

    teams = set()

    for game in games:
        teams.add(game["home_team_name"])
        teams.add(game["away_team_name"])

    saved = 0

    for team in teams:
        prior = prior_for_team(team)

        row = {
            "team_name": team,
            **prior,
        }

        supabase.table("soccer_team_global_priors").upsert(
            row,
            on_conflict="team_name",
        ).execute()

        saved += 1

    print(f"✅ Global team priors upserted: {saved}")


if __name__ == "__main__":
    main()