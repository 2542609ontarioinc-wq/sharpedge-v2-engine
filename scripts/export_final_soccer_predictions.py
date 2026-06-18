import csv
from pathlib import Path

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    rows = (
        supabase.table("final_soccer_predictions")
        .select("*")
        .order("ensemble_score", desc=True)
        .execute()
        .data
    )

    out_dir = Path("exports")
    out_dir.mkdir(exist_ok=True)

    file_path = out_dir / "final_soccer_predictions.csv"

    fields = [
        "home_team_name",
        "away_team_name",
        "best_pick",
        "market",
        "confidence",
        "ensemble_score",
        "value_rating",
        "bookmaker",
        "odds_decimal",
        "odds_american",
        "market_implied_probability",
        "model_edge",
    ]

    with file_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})

    print(f"✅ Export created: {file_path}")


if __name__ == "__main__":
    main()
    