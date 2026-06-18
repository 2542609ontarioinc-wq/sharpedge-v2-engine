from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


TABLES = [
    "games",
    "priority_leagues",
    "soccer_historical_results",
    "soccer_form_features",
    "soccer_match_strength",
    "soccer_home_away_strength",
    "soccer_prediction_versions",
    "soccer_goals_prediction_versions",
    "soccer_btts_prediction_versions",
    "soccer_odds",
    "soccer_clv_tracking",
    "soccer_data_quality_gate",
    "soccer_market_league_calibration",
    "soccer_roi_market_bookmaker_league",
    "soccer_cards_predictions",
    "soccer_corners_predictions",
    "soccer_ensemble_predictions",
    "final_soccer_predictions",
    "soccer_premium_rankings",
    "soccer_parlays",
]


def count_table(table):
    rows = (
        supabase.table(table)
        .select("id")
        .limit(5000)
        .execute()
        .data
    )

    return len(rows)


def main():
    print("SOCCER A-Z ENGINE STATUS")
    print("------------------------")

    for table in TABLES:
        try:
            count = count_table(table)
            print(f"{table}: {count}")
        except Exception as e:
            print(f"{table}: ERROR - {e}")

    print("\n✅ Soccer A-Z status check complete")


if __name__ == "__main__":
    main()
    