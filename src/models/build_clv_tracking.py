from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    grades = (
        supabase.table("soccer_prediction_grades")
        .select("*")
        .execute()
        .data
    )

    saved = 0

    for row in grades:
        # Placeholder until Odds API line movement is stored.
        opening_odds = -110
        closing_odds = -115

        clv_diff = closing_odds - opening_odds
        beat_line = clv_diff < 0

        supabase.table("soccer_clv_tracking").insert(
            {
                "game_id": row["game_id"],
                "market": "winner",
                "opening_odds": opening_odds,
                "closing_odds": closing_odds,
                "clv_difference": clv_diff,
                "beat_closing_line": beat_line,
            }
        ).execute()

        saved += 1

    print(f"✅ CLV rows created: {saved}")


if __name__ == "__main__":
    main()