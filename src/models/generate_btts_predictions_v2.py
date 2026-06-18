from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    rows = (
        supabase.table("soccer_goals_prediction_versions")
        .select("*")
        .eq("model_version", "goals_dc_v3")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )

    saved = 0

    for row in rows:
        home_xg = float(row["expected_home_goals"])
        away_xg = float(row["expected_away_goals"])

        if home_xg >= 1.3 and away_xg >= 1.3:
            yes = 68
        elif home_xg >= 1.1 and away_xg >= 1.1:
            yes = 60
        elif home_xg >= 0.9 and away_xg >= 0.9:
            yes = 52
        else:
            yes = 38

        no = 100 - yes

        if yes >= no:
            pick = "BTTS Yes"
            confidence = yes
        else:
            pick = "BTTS No"
            confidence = no

        prediction = {
            "game_id": row["game_id"],
            "model_version": "btts_ml_v2",
            "home_team_name": row["home_team_name"],
            "away_team_name": row["away_team_name"],
            "expected_home_goals": home_xg,
            "expected_away_goals": away_xg,
            "btts_yes_probability": yes,
            "btts_no_probability": no,
            "predicted_btts": pick,
            "confidence_score": confidence,
        }

        supabase.table("soccer_btts_prediction_versions").insert(prediction).execute()
        saved += 1

    print(f"✅ BTTS ML V2 predictions created: {saved}")


if __name__ == "__main__":
    main()
    