from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def bucket(confidence):
    confidence = int(confidence)

    if confidence < 40:
        return 30
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

    buckets = {}

    for row in grades:
        result = row.get("winner_grade")
        confidence = 60

        b = bucket(confidence)

        if b not in buckets:
            buckets[b] = {"total": 0, "wins": 0, "losses": 0}

        buckets[b]["total"] += 1

        if result == "win":
            buckets[b]["wins"] += 1
        else:
            buckets[b]["losses"] += 1

    for b, stats in buckets.items():
        actual = round(stats["wins"] * 100 / stats["total"], 2) if stats["total"] else 0

        supabase.table("confidence_calibration").insert(
            {
                "prediction_type": "winner",
                "confidence_bucket": b,
                "total_predictions": stats["total"],
                "wins": stats["wins"],
                "losses": stats["losses"],
                "actual_win_rate": actual,
            }
        ).execute()

    print(f"✅ Confidence calibration rows created: {len(buckets)}")


if __name__ == "__main__":
    main()
    