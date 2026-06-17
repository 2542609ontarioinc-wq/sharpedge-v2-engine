import subprocess
import time

COMMANDS = [
    "python -m src.ingestion.sync_soccer_live_odds_snapshots",
    "python -m src.ingestion.sync_soccer_live_lineups",
    "python -m src.models.build_soccer_safety_engine_v3",
    "python -m src.models.build_soccer_elite_score",
    "python -m src.models.build_soccer_promotion_events",
]

def run(cmd):
    print("\nRUNNING:", cmd)
    subprocess.run(cmd, shell=True, check=True)

def main():
    for cmd in COMMANDS:
        run(cmd)
    print("\n✅ Live monitor completed")

if __name__ == "__main__":
    main()