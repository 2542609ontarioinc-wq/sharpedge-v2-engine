from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def main():
    rows = (
        supabase.table("soccer_match_strength")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )

    saved = 0

    for row in rows:
        home_form = float(row["home_form_score"])
        away_form = float(row["away_form_score"])
        form_diff = float(row["form_difference"])

        home_advantage = 5

        form_component = form_diff * 0.45
        home_component = home_advantage

        raw_home = 33 + form_component + home_component
        raw_away = 33 - form_component
        raw_draw = 100 - raw_home - raw_away

        raw_draw = clamp(raw_draw, 12, 32)

        total = raw_home + raw_draw + raw_away

        home_prob = round((raw_home / total) * 100, 2)
        draw_prob = round((raw_draw / total) * 100, 2)
        away_prob = round((raw_away / total) * 100, 2)

        if home_prob > away_prob and home_prob > draw_prob:
            winner = row["home_team_name"]
            confidence = home_prob
        elif away_prob > home_prob and away_prob > draw_prob:
            winner = row["away_team_name"]
            confidence = away_prob
        else:
            winner = "Draw"
            confidence = draw_prob

        prediction = {
            "game_id": row["game_id"],
            "model_version": "winner_ml_v2",
            "home_team_name": row["home_team_name"],
            "away_team_name": row["away_team_name"],
            "home_probability": home_prob,
            "draw_probability": draw_prob,
            "away_probability": away_prob,
            "predicted_winner": winner,
            "confidence_score": round(confidence, 2),
            "form_difference": form_diff,
            "goal_difference_edge": 0,
            "home_advantage_score": home_advantage,
        }

        supabase.table("soccer_prediction_versions").insert(prediction).execute()
        saved += 1

    print(f"✅ Winner ML V2 predictions created: {saved}")


if __name__ == "__main__":
    main()
    