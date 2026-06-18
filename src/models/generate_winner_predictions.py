from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def probabilities_from_diff(diff):
    if diff >= 60:
        return 78, 14, 8
    if diff >= 35:
        return 68, 20, 12
    if diff >= 20:
        return 60, 25, 15
    if diff >= 8:
        return 52, 28, 20
    if diff <= -60:
        return 8, 14, 78
    if diff <= -35:
        return 12, 20, 68
    if diff <= -20:
        return 15, 25, 60
    if diff <= -8:
        return 20, 28, 52
    return 36, 28, 36


def main():
    rows = (
        supabase.table("soccer_match_strength")
        .select("*")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data
    )

    saved = 0

    for row in rows:
        diff = float(row["form_difference"])

        home_prob, draw_prob, away_prob = probabilities_from_diff(diff)

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
            "home_team_name": row["home_team_name"],
            "away_team_name": row["away_team_name"],
            "home_win_probability": home_prob,
            "draw_probability": draw_prob,
            "away_win_probability": away_prob,
            "predicted_winner": winner,
            "confidence_score": confidence,
            "model_version": "winner_form_v1",
        }

        supabase.table("soccer_prediction_results").insert(prediction).execute()
        saved += 1

    print(f"✅ Winner predictions created: {saved}")


if __name__ == "__main__":
    main()
    