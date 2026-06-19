"""
Compute and store per-model analytics for all MLB model versions.

Sources:
  mlb_model_grades      — win/loss/ROI per (game_id, model_version)
  mlb_run_predictions   — expected runs for MAE / Brier vs actuals
  games                 — actual scores for finished games

Writes one summary row per model_version to mlb_model_analytics.

Honest ordering of evidence:
  PRIMARY:   mae_total_xr, brier_score  — calibration vs reality
  PRIMARY:   avg_clv                    — null until closing-odds are captured
  SECONDARY: win_rate, roi_percent      — subject to favorites bias; do not promote
                                          a model based on these alone
"""
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"
VERSIONS = [
    "poisson_v2",
    "poisson_v3_bullpen",
    "poisson_v4_lineup",
    "poisson_v5_environment",
    "poisson_v6_form",
    "poisson_v7_statcast",
]
FINISHED_STATUSES = {
    "ft", "aot", "post", "f", "final", "game finished", "finished",
    "FT", "AOT", "POST", "F", "FINAL", "GAME FINISHED",
}


def _safe(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _mae(errors):
    return round(sum(abs(e) for e in errors) / len(errors), 4) if errors else None


def _brier(prob_pct, outcome):
    p = prob_pct / 100.0
    return (p - outcome) ** 2


def main():
    # Finished games with scores
    games = (
        supabase.table("games")
        .select("id,home_team_name,away_team_name,home_score,away_score,status")
        .eq("sport_key", SPORT_KEY)
        .execute()
        .data
    )
    finished = {
        g["id"]: g for g in games
        if (g.get("status") or "").lower() in FINISHED_STATUSES
        and _safe(g.get("home_score")) is not None
        and _safe(g.get("away_score")) is not None
    }

    # Grades per model
    grades_raw = supabase.table("mlb_model_grades").select("*").execute().data
    grades_by_ver = defaultdict(list)
    for gr in grades_raw:
        grades_by_ver[gr.get("model_version")].append(gr)

    # Run predictions per model (for MAE / Brier / O85 accuracy)
    preds_raw = (
        supabase.table("mlb_run_predictions")
        .select(
            "game_id,model_version,expected_home_runs,expected_away_runs,"
            "home_win_probability,over_85_probability"
        )
        .in_("model_version", VERSIONS)
        .execute()
        .data
    )
    preds_by_ver = defaultdict(dict)
    for p in preds_raw:
        gid = p.get("game_id")
        ver = p.get("model_version")
        if gid and ver:
            preds_by_ver[ver][gid] = p

    now = datetime.now(ZoneInfo("UTC")).isoformat()
    saved = 0

    print("\nMLB MODEL ANALYTICS")
    print("=" * 80)
    print(
        f"  NOTE: MAE and Brier are the PRIMARY quality signals.\n"
        f"  win_rate/ROI are secondary — a model picking more favorites\n"
        f"  can show higher win_rate while being less calibrated.\n"
        f"  CLV is null until closing-odds capture is implemented.\n"
    )

    for ver in VERSIONS:
        ver_grades = grades_by_ver.get(ver, [])
        ver_preds = preds_by_ver.get(ver, {})

        # Grade-based metrics
        total = len(ver_grades)
        wins = sum(1 for g in ver_grades if g.get("grade") == "WIN")
        real_odds_grades = [
            g for g in ver_grades
            if not g.get("no_odds") and g.get("grade") in ("WIN", "LOSS")
        ]
        roi_units = sum(_safe(g.get("units_result")) or 0 for g in real_odds_grades)
        wins_real = sum(1 for g in real_odds_grades if g.get("grade") == "WIN")

        win_rate = round(wins / total, 4) if total else None
        win_rate_real = round(wins_real / len(real_odds_grades), 4) if real_odds_grades else None
        roi_pct = round(roi_units / len(real_odds_grades) * 100, 2) if real_odds_grades else None

        # Prediction-based metrics (vs finished actuals)
        xr_errs = []
        brier_scores = []
        over85_correct = over85_total = 0
        dir_correct = dir_total = 0

        for gid, pred in ver_preds.items():
            game = finished.get(gid)
            if not game:
                continue
            ah = _safe(game["home_score"])
            aa = _safe(game["away_score"])
            if ah is None or aa is None:
                continue

            xh = _safe(pred.get("expected_home_runs"))
            xa = _safe(pred.get("expected_away_runs"))
            if xh is not None and xa is not None:
                xr_errs.append((xh + xa) - (ah + aa))

            hw = _safe(pred.get("home_win_probability"))
            if hw is not None:
                actual_hw = 1 if ah > aa else 0
                dir_correct += (1 if hw > 50 else 0) == actual_hw
                dir_total += 1
                brier_scores.append(_brier(hw, actual_hw))

            o85 = _safe(pred.get("over_85_probability"))
            if o85 is not None:
                over85_correct += (o85 > 50) == (ah + aa > 8.5)
                over85_total += 1

        mae = _mae(xr_errs)
        brier = round(sum(brier_scores) / len(brier_scores), 5) if brier_scores else None
        over85_acc = round(over85_correct / over85_total, 4) if over85_total else None
        dir_acc = round(dir_correct / dir_total, 4) if dir_total else None

        row = {
            "model_version": ver,
            "games_graded": total,
            "picks_with_real_odds": len(real_odds_grades),
            "mae_total_xr": mae,
            "brier_score": brier,
            "over85_accuracy": over85_acc,
            "direction_accuracy": dir_acc,
            "win_rate": win_rate,
            "win_rate_real_odds": win_rate_real,
            "roi_units": round(roi_units, 3) if real_odds_grades else None,
            "roi_percent": roi_pct,
            "avg_clv": None,
            "updated_at": now,
        }

        supabase.table("mlb_model_analytics").upsert(
            row, on_conflict="model_version"
        ).execute()

        mae_str = f"{mae:.3f}" if mae is not None else "—"
        wr_str = f"{win_rate:.1%}" if win_rate is not None else "—"
        roi_str = f"{roi_pct:+.1f}%" if roi_pct is not None else "—"
        print(
            f"  {ver:30s} n={total:3d} | MAE={mae_str} | WR={wr_str} | ROI={roi_str}"
        )
        saved += 1

    print(f"\n✅ MLB model analytics updated: {saved} versions")


if __name__ == "__main__":
    main()
