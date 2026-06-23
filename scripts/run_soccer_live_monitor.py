import subprocess
import time

COMMANDS = [
    "python -m src.ingestion.sync_soccer_live_odds_snapshots",
    "python -m src.ingestion.sync_soccer_live_lineups",
    "python -m src.models.build_soccer_safety_engine_v3",
    "python -m src.models.build_soccer_elite_score",
    "python -m src.models.build_soccer_promotion_events",
    "python -m src.grading.grade_soccer_picks",
    "python -m src.analytics.build_soccer_adaptive_weights",
    "python -m src.analytics.apply_soccer_adaptive_weights",
    "python -m src.models.build_soccer_master_picks",
    "python -m src.analytics.build_soccer_analytics_feedback",
    "python -m src.models.build_soccer_clv_tracker",
    # Refresh the soccer_pick_results aggregate so TrackRecordView stays current.
    # grade_soccer_results re-runs grade_soccer_picks internally (harmless upsert).
    "python -m src.models.grade_soccer_results",
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