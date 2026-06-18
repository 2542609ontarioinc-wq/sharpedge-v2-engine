from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    rows = (
        supabase.table("confidence_calibration")
        .select("*")
        .order("confidence_bucket")
        .execute()
        .data
    )

    print(f"Calibration buckets: {len(rows)}")

    for row in rows:
        print(
            f"Bucket {row['confidence_bucket']} | "
            f"Predictions: {row['total_predictions']} | "
            f"Wins: {row['wins']} | "
            f"Losses: {row['losses']} | "
            f"Actual: {row['actual_win_rate']}%"
        )


if __name__ == "__main__":
    main()
    