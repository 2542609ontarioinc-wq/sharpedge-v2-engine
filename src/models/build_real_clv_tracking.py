from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    odds = (
        supabase.table("soccer_odds")
        .select("*")
        .not_.is_("game_id", "null")
        .order("captured_at")
        .execute()
        .data
    )

    grouped = {}

    for row in odds:
        key = (
            row["game_id"],
            row["market"],
            row["selection"],
            row["bookmaker"],
        )

        grouped.setdefault(key, []).append(row)

    saved = 0

    for key, rows in grouped.items():
        opening = rows[0]
        closing = rows[-1]

        opening_odds = float(opening["odds_decimal"])
        closing_odds = float(closing["odds_decimal"])

        clv_diff = round(closing_odds - opening_odds, 3)
        beat = clv_diff > 0

        supabase.table("soccer_clv_tracking").insert(
            {
                "game_id": opening["game_id"],
                "market": opening["market"],
                "opening_odds": opening_odds,
                "closing_odds": closing_odds,
                "clv_difference": clv_diff,
                "beat_closing_line": beat,
            }
        ).execute()

        saved += 1

    print(f"✅ Real CLV rows created: {saved}")


if __name__ == "__main__":
    main()
    