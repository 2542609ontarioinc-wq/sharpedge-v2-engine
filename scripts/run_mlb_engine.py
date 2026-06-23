"""
MLB Sharp Engine — daily run script.

Stage order:
  1. Ingest games + odds (alt markets and player props combined into per-event call)
  2. Starting pitchers from MLB Stats API (free, keyless)
  2b. Bullpen strength from MLB Stats API (one extra call; feeds v3 comparison model)
  3. Batting lineups from MLB Stats API (when confirmed; skips if too early)
  3b. Batter split stats + pitcher handedness (vL/vR; feeds v4 lineup shadow model)
  4. Team run-scoring/allowing strength
  5. Poisson run model → writes poisson_v2 (production), v3_bullpen, v4_lineup (shadows)
  6. Game-level final picks: multi-market selection + honest calibration + Safe Zone
  7. Player prop predictions: pitcher K/Outs/ER/H/BB + batter H+R+RBI
  8. Grade settled game picks + prop picks
  9. Backtest on historical results
"""
import subprocess

COMMANDS = [
    # 1. Ingest: games + odds (props fetched in same per-event call as alt markets)
    "python -m src.ingestion.sync_mlb_games",
    "python -m src.ingestion.sync_mlb_odds",

    # 2. Starting pitchers from MLB Stats API
    "python -m src.ingestion.sync_mlb_pitchers",

    # 2b. Bullpen strength (1 free API call; skips gracefully if table missing)
    "python -m src.ingestion.sync_mlb_bullpen",

    # 3. Batting lineups (skips gracefully if not yet confirmed)
    "python -m src.ingestion.sync_mlb_lineups",

    # 3b. Batter split stats (vL/vR OPS) + pitcher handedness for v4 lineup shadow model
    "python -m src.ingestion.sync_mlb_batter_stats",

    # 4. Team strength
    "python -m src.features.build_mlb_team_strength",

    # 5. Poisson run model (writes v2 production + v3 bullpen shadow for comparison)
    "python -m src.models.generate_mlb_run_predictions",

    # 6. Game-level picks: moneyline / totals / run-line + Safe Zone (v2 production only)
    "python -m src.models.build_mlb_final_picks",

    # 6b. Per-model picks for all versions (v2–v7) — shadow/comparison only
    "python -m src.models.build_mlb_model_picks",

    # 7. Player props: pitcher K/Outs (solid) + ER/H/BB (noisier) + batter H+R+RBI
    "python -m src.models.generate_mlb_player_props",

    # 8. Grade settled picks (game + props)
    "python -m src.models.grade_mlb_results",

    # 8b. Grade per-model picks (v2–v7 shadow comparison)
    "python -m src.grading.grade_mlb_model_picks",

    # 8c. Compute per-model analytics (MAE primary, win-rate/ROI secondary)
    "python -m src.analytics.build_mlb_model_analytics",

    # 9. Backtest
    "python -m scripts.backtest_mlb_model",

    # 10. CLV: compute closing-line value per graded pick, aggregate into track record.
    #     Requires mlb_odds_snapshots to have both an opening (from stage 2) and at least
    #     one hourly closing snapshot (from snap_mlb_odds_closing in the refresh job).
    #     Picks with no closing snapshot are excluded from CLV stats, not counted as 0.
    "python -m src.models.build_mlb_clv",

    # 11. Build enriched per-pick / per-prop diagnostic detail rows (with subscriber flags).
    #     Must run after grade_mlb_results (step 8) and build_mlb_clv (step 10).
    "python -m src.grading.build_mlb_pick_detail",
    "python -m src.grading.build_mlb_prop_detail",

    # (step 12 removed — build_mlb_subscriber_analytics writes mlb_subscriber_results
    #  which is never read by the frontend; track record computed client-side from
    #  mlb_pick_detail via computeSegment(). Re-add if mlb_subscriber_results is wired up.)
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
