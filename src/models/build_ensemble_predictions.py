from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def latest(table, game_id):
    rows = (
        supabase.table(table)
        .select("*")
        .eq("game_id", game_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else None


def rating(score):
    if score >= 75:
        return "Elite"
    if score >= 65:
        return "Strong"
    if score >= 55:
        return "Playable"
    return "Pass"


def main():
    winner_rows = (
        supabase.table("soccer_prediction_versions")
        .select("*")
        .eq("model_version", "winner_dc_v3")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )

    saved = 0

    for win in winner_rows:
        game_id = win["game_id"]

        goals = latest("soccer_goals_prediction_versions", game_id)
        btts = latest("soccer_btts_prediction_versions", game_id)

        if not goals or not btts:
            continue

        over25 = float(goals["over_25_probability"])
        under25 = float(goals["under_25_probability"])

        if over25 >= under25:
            goals_pick = "Over 2.5"
            goals_conf = over25
        else:
            goals_pick = "Under 2.5"
            goals_conf = under25

        score = round(
            (
                float(win["confidence_score"]) * 0.45
                + goals_conf * 0.30
                + float(btts["confidence_score"]) * 0.25
            ),
            2,
        )

        row = {
            "game_id": game_id,
            "home_team_name": win["home_team_name"],
            "away_team_name": win["away_team_name"],
            "winner_pick": win["predicted_winner"],
            "winner_confidence": win["confidence_score"],
            "goals_pick": goals_pick,
            "goals_confidence": goals_conf,
            "btts_pick": btts["predicted_btts"],
            "btts_confidence": btts["confidence_score"],
            "ensemble_score": score,
            "value_rating": rating(score),
        }

        supabase.table("soccer_ensemble_predictions").upsert(row, on_conflict="game_id").execute()
        saved += 1

    print(f"✅ Ensemble predictions created: {saved}")


if __name__ == "__main__":
    main()
    