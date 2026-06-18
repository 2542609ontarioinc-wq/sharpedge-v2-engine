from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def calc_roi(market, grade_field):
    rows = (
        supabase.table("soccer_prediction_grades")
        .select("*")
        .execute()
        .data
    )

    wins = sum(1 for r in rows if r[grade_field] == "win")
    losses = sum(1 for r in rows if r[grade_field] == "loss")
    total = wins + losses

    stake = 1
    total_staked = total * stake

    # Simple flat model at -110 odds:
    # win profit = 0.91 units, loss = -1 unit
    profit = round((wins * 0.91) - losses, 2)

    roi = round((profit / total_staked) * 100, 2) if total_staked else 0

    row = {
        "market": market,
        "total_bets": total,
        "wins": wins,
        "losses": losses,
        "stake_per_bet": stake,
        "total_staked": total_staked,
        "profit_units": profit,
        "roi_percentage": roi,
    }

    supabase.table("soccer_roi_tracking").insert(row).execute()


def main():
    calc_roi("winner", "winner_grade")
    calc_roi("over_25", "over_25_grade")
    calc_roi("btts", "btts_grade")

    print("✅ ROI tracking created")


if __name__ == "__main__":
    main()
    