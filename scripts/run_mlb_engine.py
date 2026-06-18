"""
MLB Sharp Engine — daily run script.

Stage order:
  1. Ingest games (upcoming + recent history for backtest)
  2. Fetch odds from The Odds API
  3. Build team run-scoring/allowing strength (shrunk Poisson indices)
  4. Poisson run model → moneyline / totals / run-line probabilities
  5. Final picks: multi-market selection + honest calibration + Safe Zone
  6. Backtest on settled results (prints accuracy + saves to mlb_backtest_results)

Props are a separate later module — this engine intentionally stops at game-level picks.
"""
import subprocess

COMMANDS = [
    # 1. Ingest: games + odds
    "python -m src.ingestion.sync_mlb_games",
    "python -m src.ingestion.sync_mlb_odds",

    # 2. Starting pitchers from MLB Stats API (free, keyless) — must run after games sync
    "python -m src.ingestion.sync_mlb_pitchers",

    # 3. Team strength (must run after game results are current)
    "python -m src.features.build_mlb_team_strength",

    # 3. Poisson predictions for today's slate
    "python -m src.models.generate_mlb_run_predictions",

    # 4. Multi-market selection + honest calibration + Safe Zone
    "python -m src.models.build_mlb_final_picks",

    # 5. Backtest on historical results
    "python -m scripts.backtest_mlb_model",
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
    print("MLB SHARP ENGINE RUN COMPLETE")
    print("=" * 60)
    if failed:
        print(f"{len(failed)} step(s) failed:")
        for f in failed:
            print("  -", f)
    else:
        print("All steps succeeded.")


if __name__ == "__main__":
    main()
