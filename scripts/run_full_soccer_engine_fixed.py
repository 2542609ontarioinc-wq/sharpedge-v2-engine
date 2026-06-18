import subprocess
COMMANDS = [
    "python -m scripts.sync_next_3_days_soccer",
    "python -m src.ingestion.sync_soccer_details",
    "python -m src.ingestion.sync_soccer_odds",
    "python -m src.ingestion.match_odds_to_games",
    "python -m src.ingestion.sync_historical_results",
    "python -m src.ingestion.build_soccer_team_stat_history",
    "python -m src.features.build_soccer_team_rolling_features",
    "python -m src.features.build_soccer_team_advanced_rolling_features",
    "python -m src.features.build_soccer_opponent_strength",
    "python -m src.features.build_soccer_team_style_profiles",
    "python -m src.features.build_soccer_league_baselines",
    "python -m src.features.build_soccer_referee_history",
    "python -m src.features.build_soccer_team_global_priors",
    "python -m src.features.build_soccer_team_profile_fallbacks",
    "python -m src.features.build_team_form_features",
    "python -m src.features.build_match_strength",
    "python -m src.features.build_home_away_strength",
    "python -m src.features.build_soccer_rest_travel_features",
    "python -m src.features.build_lineup_impact",
    "python -m src.features.build_injury_impact",
    "python -m src.models.generate_winner_predictions_v2",
    "python -m src.models.generate_goals_predictions_v2",
    "python -m src.models.generate_btts_predictions_v2",
    "python -m src.models.build_ensemble_predictions",
    "python -m src.models.build_final_predictions",
    "python -m src.models.fix_final_prediction_odds",
    "python -m src.models.build_data_quality_gate",
    "python -m src.models.build_premium_rankings",
    "python -m src.models.build_parlay_builder",
    "python -m src.features.build_soccer_match_features",
    "python -m src.ingestion.build_soccer_market_snapshots",
    "python -m src.features.build_real_soccer_weather_features",
    "python -m src.features.build_soccer_match_features_pro",
    "python -m src.features.apply_soccer_global_priors",
    "python -m src.features.apply_soccer_profile_fallbacks",
    "python -m src.features.build_soccer_matchup_features",
    "python -m src.models.build_soccer_market_value",
    "python -m src.models.build_soccer_model_safety_flags",
    "python -m src.models.apply_safety_to_market_value",
    "python -m src.models.build_soccer_calibrated_value",
    "python -m src.models.build_final_pro_soccer_picks",
    "python -m scripts.clean_soccer_duplicates",
]
def run(cmd):
    print("\n====================================")
    print("RUNNING:", cmd)
    print("====================================")
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0:
        print("STEP FAILED (continuing):", cmd)
def main():
    for cmd in COMMANDS:
        run(cmd)
    print("\nFULL SOCCER ENGINE (FIXED) COMPLETED")
if __name__ == "__main__":
    main()
