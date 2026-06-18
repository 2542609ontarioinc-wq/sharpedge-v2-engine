import subprocess

COMMANDS = [
    "python -m scripts.sync_next_3_days_soccer",
    "python -m src.ingestion.sync_soccer_odds",
    "python -m src.ingestion.match_odds_to_games",

    "python -m src.features.build_team_form_features",
    "python -m src.features.build_match_strength",
    "python -m src.features.build_home_away_strength",
    "python -m src.features.build_lineup_impact",
    "python -m src.features.build_injury_impact",

    "python -m src.models.generate_winner_predictions_v2",
    "python -m src.models.generate_goals_predictions_v2",
    "python -m src.models.generate_btts_predictions_v2",
    "python -m src.models.build_ensemble_predictions",
    "python -m src.models.build_final_predictions",
    "python -m src.models.update_final_predictions_with_odds",
    "python -m src.models.build_premium_rankings",
    "python -m src.models.build_parlay_builder",

    "python -m src.features.build_soccer_match_features",
    "python -m src.ingestion.build_soccer_market_snapshots",
    "python -m src.features.build_real_soccer_weather_features",
    "python -m src.features.build_soccer_match_features_pro",
    "python -m src.features.apply_soccer_global_priors",
    "python -m src.features.build_soccer_matchup_features",

    "python -m src.models.fix_final_prediction_odds",
    "python -m src.models.build_soccer_market_value",
    "python -m src.models.build_soccer_model_safety_flags",
    "python -m src.models.apply_safety_to_market_value",
    "python -m src.models.build_soccer_calibrated_value",
    "python -m src.models.build_final_pro_soccer_picks",

    "python -m scripts.clean_soccer_duplicates",
    "python -m scripts.check_soccer_api_ready_view",
    "python -m scripts.check_today_soccer_watchlist",
]

def run(cmd):
    print("\n====================================")
    print("RUNNING:", cmd)
    print("====================================")
    subprocess.run(cmd, shell=True, check=True)

def main():
    for cmd in COMMANDS:
        run(cmd)
    print("\n✅ FULL SOCCER ENGINE COMPLETED")

if __name__ == "__main__":
    main()
    