from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    predictions = (
        supabase.table("soccer_prediction_results")
        .select("*")
        .execute()
        .data
    )

    saved = 0

    for prediction in predictions:
        game_id = prediction["game_id"]

        game = (
            supabase.table("games")
            .select("external_game_id")
            .eq("id", game_id)
            .limit(1)
            .execute()
            .data
        )

        if not game:
            continue

        fixture_id = game[0]["external_game_id"]

        result_rows = (
            supabase.table("soccer_historical_results")
            .select("*")
            .eq("fixture_id", fixture_id)
            .limit(1)
            .execute()
            .data
        )

        if not result_rows:
            continue

        actual = result_rows[0]

        predicted = prediction["predicted_winner"]

        if actual["result"] == "home":
            actual_winner = prediction["home_team_name"]
        elif actual["result"] == "away":
            actual_winner = prediction["away_team_name"]
        else:
            actual_winner = "Draw"

        winner_grade = "win" if predicted == actual_winner else "loss"

        goal_rows = (
            supabase.table("soccer_goal_predictions")
            .select("*")
            .eq("game_id", game_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )

        over_25_prediction = None
        over_25_grade = None
        btts_prediction = None
        btts_grade = None

        if goal_rows:
            goal = goal_rows[0]

            over_25_prediction = (
                "over_25"
                if goal["over_25_probability"] >= 55
                else "under_25"
            )

            actual_over_25 = actual["total_goals"] > 2.5

            over_25_grade = (
                "win"
                if (
                    (over_25_prediction == "over_25" and actual_over_25)
                    or (over_25_prediction == "under_25" and not actual_over_25)
                )
                else "loss"
            )

            btts_prediction = (
                "btts_yes"
                if goal["btts_yes_probability"] >= 55
                else "btts_no"
            )

            actual_btts = actual["btts"]

            btts_grade = (
                "win"
                if (
                    (btts_prediction == "btts_yes" and actual_btts)
                    or (btts_prediction == "btts_no" and not actual_btts)
                )
                else "loss"
            )
        else:
            actual_over_25 = None
            actual_btts = None

        row = {
            "game_id": game_id,
            "home_team_name": prediction["home_team_name"],
            "away_team_name": prediction["away_team_name"],
            "predicted_winner": predicted,
            "actual_result": actual_winner,
            "winner_grade": winner_grade,
            "over_25_prediction": over_25_prediction,
            "actual_over_25": actual_over_25,
            "over_25_grade": over_25_grade,
            "btts_prediction": btts_prediction,
            "actual_btts": actual_btts,
            "btts_grade": btts_grade,
        }

        supabase.table("soccer_prediction_grades").insert(row).execute()
        saved += 1

    print(f"✅ Prediction grades created: {saved}")


if __name__ == "__main__":
    main()
    