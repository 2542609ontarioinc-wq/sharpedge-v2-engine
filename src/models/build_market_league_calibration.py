from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def bucket(confidence):
    confidence = int(confidence)

    if confidence < 50:
        return 40
    if confidence < 60:
        return 50
    if confidence < 70:
        return 60
    if confidence < 80:
        return 70
    return 80


def main():
    grades = (
        supabase.table("soccer_prediction_grades")
        .select("*")
        .execute()
        .data
    )

    grouped = {}

    for grade in grades:
        game_rows = (
            supabase.table("games")
            .select("league_key")
            .eq("id", grade["game_id"])
            .limit(1)
            .execute()
            .data
        )

        league_key = game_rows[0]["league_key"] if game_rows else None

        markets = [
            ("winner", grade.get("winner_grade")),
            ("over_25", grade.get("over_25_grade")),
            ("btts", grade.get("btts_grade")),
        ]

        for market, result in markets:
            if result not in ["win", "loss"]:
                continue

            confidence = 60
            b = bucket(confidence)

            key = (market, league_key, b)

            if key not in grouped:
                grouped[key] = {
                    "total": 0,
                    "wins": 0,
                    "losses": 0,
                }

            grouped[key]["total"] += 1

            if result == "win":
                grouped[key]["wins"] += 1
            else:
                grouped[key]["losses"] += 1

    saved = 0

    for key, stats in grouped.items():
        market, league_key, b = key

        actual = (
            round(stats["wins"] * 100 / stats["total"], 2)
            if stats["total"]
            else 0
        )

        supabase.table("soccer_market_league_calibration").insert(
            {
                "market": market,
                "league_key": league_key,
                "confidence_bucket": b,
                "total_predictions": stats["total"],
                "wins": stats["wins"],
                "losses": stats["losses"],
                "actual_win_rate": actual,
            }
        ).execute()

        saved += 1

    print(f"✅ Market/league calibration rows created: {saved}")


if __name__ == "__main__":
    main()
    