import subprocess

# Correct order: ingest -> foundation -> features -> DC model ->
# multi-market select -> calibrate + no-vig edges -> value/safety -> picks.
# Calibration self-improves as historical match data grows.
COMMANDS = [
    # 1. Ingest games, enrichment, odds (odds now capture line numbers)
    "python -m scripts.sync_next_3_days_soccer",
    "python -m src.ingestion.sync_soccer_details",
    "python -m src.ingestion.sync_soccer_odds",
    "python -m src.ingestion.match_odds_to_games",

    # 2. History + foundation (deep history is capped to priority teams)
    "python -m src.ingestion.sync_historical_results",
    "python -m src.ingestion.sync_team_deep_history",
    "python -m src.ingestion.build_soccer_team_stat_history",
    "python -m src.features.build_soccer_team_rolling_features",
    "python -m src.features.build_soccer_team_advanced_rolling_features",
    "python -m src.features.build_soccer_opponent_strength",
    "python -m src.features.build_soccer_team_style_profiles",
    "python -m src.features.build_soccer_league_baselines",
    "python -m src.features.build_soccer_referee_history",
    "python -m src.features.build_soccer_team_global_priors",
    "python -m src.features.build_soccer_team_profile_fallbacks",

    # 3. Per-game base features
    "python -m src.features.build_team_form_features",
    "python -m src.features.build_match_strength",
    "python -m src.features.build_home_away_strength",
    "python -m src.features.build_soccer_rest_travel_features",
    "python -m src.features.build_lineup_impact",
    "python -m src.features.build_injury_impact",

    # 4. Dixon-Coles engine -> all markets
    "python -m src.models.generate_goals_predictions_v3_dixoncoles",
    "python -m src.models.generate_btts_predictions_v2",
    "python -m src.models.build_ensemble_predictions",
    "python -m src.models.build_cards_model",
    "python -m src.models.build_corners_model",

    # 5. Multi-market selection (Sharp + Safe Zone)
    "python -m src.models.build_final_predictions_multimarket",

    # 6. Honesty layer: refresh calibration map + apply shrink + no-vig edges
    "python -m src.models.build_calibration_map",
    "python -m src.models.apply_honest_calibration",

    # 7. Data quality gate (now sees calibrated conf + real odds)
    "python -m src.models.build_data_quality_gate",

    # 8. Pro features + value/safety -> final published picks
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

    # 9. Cleanup
    "python -m scripts.clean_soccer_duplicates",
]


def main():
    failed = []
    for i, cmd in enumerate(COMMANDS, 1):
        print(f"\n[{i}/{len(COMMANDS)}] {cmd}")
        print("=" * 60)
        r = subprocess.run(cmd, shell=True)
        if r.returncode != 0:
            print(f"!! STEP FAILED: {cmd}")
            failed.append(cmd)

    print("\n" + "=" * 60)
    print("SHARP ENGINE RUN COMPLETE")
    print("=" * 60)
    if failed:
        print(f"{len(failed)} step(s) failed:")
        for f in failed:
            print("  -", f)
    else:
        print("All steps succeeded.")


if __name__ == "__main__":
    main()
