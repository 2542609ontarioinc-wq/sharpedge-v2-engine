from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def clamp(value, low, high):
    return max(low, min(high, value))


def goals_from_form(form_score, goals_for, goals_against):
    form_part = form_score / 50
    attack_part = goals_for / 5 if goals_for else 1
    defense_penalty = goals_against / 10 if goals_against else 0

    xg = 1.1 + (form_part * 0.35) + (attack_part * 0.25) - defense_penalty
    return round(clamp(xg, 0.5, 3.2), 2)


def get_latest_form(game_id, team_name):
    rows = (
        supabase.table("soccer_form_features")
        .select("*")
        .eq("game_id", game_id)
        .eq("team_name", team_name)
        .gt("matches_checked", 0)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )

    return rows[0] if rows else None


def probability_from_total(total):
    over15 = clamp(round(45 + total * 15, 2), 45, 92)
    over25 = clamp(round(25 + total * 14, 2), 25, 82)
    over35 = clamp(round(10 + total * 10, 2), 10, 65)

    return over15, over25, over35


def main():
    games = (
        supabase.table("soccer_match_strength")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )

    saved = 0

    for game in games:
        home_form = get_latest_form(game["game_id"], game["home_team_name"])
        away_form = get_latest_form(game["game_id"], game["away_team_name"])

        if not home_form or not away_form:
            continue

        home_xg = goals_from_form(
            float(home_form["form_score"]),
            int(home_form["goals_for"]),
            int(home_form["goals_against"]),
        )

        away_xg = goals_from_form(
            float(away_form["form_score"]),
            int(away_form["goals_for"]),
            int(away_form["goals_against"]),
        )

        total = round(home_xg + away_xg, 2)

        over15, over25, over35 = probability_from_total(total)
        under25 = round(100 - over25, 2)

        if home_xg >= 1.15 and away_xg >= 1.15:
            btts_yes = 64
        elif home_xg >= 1.0 and away_xg >= 1.0:
            btts_yes = 56
        else:
            btts_yes = 42

        btts_no = 100 - btts_yes

        row = {
            "game_id": game["game_id"],
            "model_version": "goals_ml_v2",
            "home_team_name": game["home_team_name"],
            "away_team_name": game["away_team_name"],
            "expected_home_goals": home_xg,
            "expected_away_goals": away_xg,
            "expected_total_goals": total,
            "over_15_probability": over15,
            "over_25_probability": over25,
            "over_35_probability": over35,
            "under_25_probability": under25,
            "btts_yes_probability": btts_yes,
            "btts_no_probability": btts_no,
        }

        supabase.table("soccer_goals_prediction_versions").insert(row).execute()
        saved += 1

    print(f"✅ Goals ML V2 predictions created: {saved}")


if __name__ == "__main__":
    main()
    