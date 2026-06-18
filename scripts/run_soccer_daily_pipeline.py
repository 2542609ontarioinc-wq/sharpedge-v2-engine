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

    "python -m scripts.clean_soccer_duplicates",
    "python -m scripts.check_final_predictions",
]


def run_command(command):
    print("\n====================================")
    print(f"RUNNING: {command}")
    print("====================================")

    result = subprocess.run(
        command,
        shell=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {command}")


def main():
    for command in COMMANDS:
        run_command(command)

    print("\n✅ Soccer daily pipeline completed")


if __name__ == "__main__":
    main()
    