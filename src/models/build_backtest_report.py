from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def accuracy(wins, losses):
    total = wins + losses
    return round((wins / total) * 100, 2) if total else 0


def main():
    rows = (
        supabase.table("soccer_prediction_grades")
        .select("*")
        .execute()
        .data
    )

    winner_wins = sum(1 for r in rows if r["winner_grade"] == "win")
    winner_losses = sum(1 for r in rows if r["winner_grade"] == "loss")

    over_wins = sum(1 for r in rows if r["over_25_grade"] == "win")
    over_losses = sum(1 for r in rows if r["over_25_grade"] == "loss")

    btts_wins = sum(1 for r in rows if r["btts_grade"] == "win")
    btts_losses = sum(1 for r in rows if r["btts_grade"] == "loss")

    report = {
        "report_name": "soccer_backtest_v1",
        "total_games": len(rows),

        "winner_wins": winner_wins,
        "winner_losses": winner_losses,
        "winner_accuracy": accuracy(winner_wins, winner_losses),

        "over_25_wins": over_wins,
        "over_25_losses": over_losses,
        "over_25_accuracy": accuracy(over_wins, over_losses),

        "btts_wins": btts_wins,
        "btts_losses": btts_losses,
        "btts_accuracy": accuracy(btts_wins, btts_losses),
    }

    supabase.table("soccer_backtest_reports").insert(report).execute()

    print("✅ Backtest report created")


if __name__ == "__main__":
    main()
    