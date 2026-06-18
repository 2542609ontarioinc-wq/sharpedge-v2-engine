from supabase import create_client

from src.config.settings import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)


def main():

    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_KEY
    )

    features = (
        supabase.table("model_features")
        .select("*")
        .eq(
            "feature_version",
            "soccer_basic_v1"
        )
        .execute()
    )

    print(
        f"Feature rows loaded: {len(features.data)}"
    )

    for row in features.data:

        prediction = {

            "game_id": row["game_id"],

            "sport_key": "soccer",

            "model_version": "soccer_v1",

            "home_win_probability": 40,

            "draw_probability": 25,

            "away_win_probability": 35,

            "expected_goals": 2.5,

            "expected_cards": 4.0,

            "expected_corners": 9.0,

            "confidence_score": 50

        }

        supabase.table(
            "predictions"
        ).insert(
            prediction
        ).execute()

    print("✅ Prediction rows created")


if __name__ == "__main__":
    main()
    