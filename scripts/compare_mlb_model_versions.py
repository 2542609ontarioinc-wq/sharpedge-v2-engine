"""
Compare poisson_v2, poisson_v3_bullpen, and poisson_v4_lineup.

  v2          — starter-only pitcher blend, team-level offense
  v3_bullpen  — explicit starter/bullpen innings split on defense
  v4_lineup   — v3 defense + lineup-aware offense (confirmed batters × handedness splits)

Joins mlb_run_predictions for all versions against finished games with actual scores.
Prints per-version: MAE for xRuns, win-prediction accuracy, Brier score, and O/U accuracy.

Run AFTER several weeks of data have accumulated:
    python -m scripts.compare_mlb_model_versions
"""
import math
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

V2 = "poisson_v2"
V3 = "poisson_v3_bullpen"
V4 = "poisson_v4_lineup"
VERSIONS = [V2, V3, V4]
SPORT_KEY = "baseball_mlb"
FINISHED_STATUSES = {"FT", "AOT", "POST", "F", "FINAL", "GAME FINISHED"}


def _safe(v, default=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _brier(prob_pct, outcome):
    """Brier score contribution for one event. prob_pct in [0,100], outcome in {0,1}."""
    p = prob_pct / 100.0
    return (p - outcome) ** 2


def _mae(errors):
    return sum(abs(e) for e in errors) / len(errors) if errors else None


def main():
    season = datetime.now(ZoneInfo("America/Toronto")).year

    # Load finished games with actual scores
    games = (
        supabase.table("games")
        .select("id,home_team_name,away_team_name,home_score,away_score,status,season")
        .eq("sport_key", SPORT_KEY)
        .eq("season", str(season))
        .execute()
        .data
    )

    finished = {
        g["id"]: g for g in games
        if (g.get("status") or "").upper() in FINISHED_STATUSES
        and _safe(g.get("home_score")) is not None
        and _safe(g.get("away_score")) is not None
    }

    if not finished:
        print("No finished games with scores found yet.")
        return

    print(f"Finished games with scores: {len(finished)}")

    # Load predictions for all versions
    preds = (
        supabase.table("mlb_run_predictions")
        .select("*")
        .in_("model_version", VERSIONS)
        .execute()
        .data
    )

    # Group by version → game_id → prediction
    by_version = defaultdict(dict)
    for p in preds:
        gid = p.get("game_id")
        ver = p.get("model_version")
        if gid and ver:
            by_version[ver][gid] = p

    results = {}
    for ver in VERSIONS:
        ver_preds = by_version.get(ver, {})
        if not ver_preds:
            print(f"\n{ver}: no predictions found — run the engine first.")
            continue

        home_xr_errs = []
        away_xr_errs = []
        total_xr_errs = []
        win_correct = 0
        win_total = 0
        brier_scores = []
        over85_correct = 0
        over85_total = 0

        for gid, pred in ver_preds.items():
            game = finished.get(gid)
            if not game:
                continue

            actual_home = _safe(game["home_score"])
            actual_away = _safe(game["away_score"])
            if actual_home is None or actual_away is None:
                continue

            xr_home = _safe(pred.get("expected_home_runs"))
            xr_away = _safe(pred.get("expected_away_runs"))
            if xr_home is None or xr_away is None:
                continue

            home_xr_errs.append(xr_home - actual_home)
            away_xr_errs.append(xr_away - actual_away)
            total_xr_errs.append((xr_home + xr_away) - (actual_home + actual_away))

            hw_prob = _safe(pred.get("home_win_probability"), 50.0)
            actual_home_win = 1 if actual_home > actual_away else 0
            predicted_home_win = 1 if hw_prob > 50 else 0
            win_correct += (predicted_home_win == actual_home_win)
            win_total += 1
            brier_scores.append(_brier(hw_prob, actual_home_win))

            actual_total = actual_home + actual_away
            over85_pred = _safe(pred.get("over_85_probability"), 50.0) > 50
            over85_actual = actual_total > 8.5
            over85_correct += (over85_pred == over85_actual)
            over85_total += 1

        n = len(home_xr_errs)
        if n == 0:
            print(f"\n{ver}: 0 matched finished games — no metrics yet.")
            continue

        results[ver] = {
            "n": n,
            "mae_home_xr": _mae(home_xr_errs),
            "mae_away_xr": _mae(away_xr_errs),
            "mae_total_xr": _mae(total_xr_errs),
            "bias_home": sum(home_xr_errs) / n,
            "bias_total": sum(total_xr_errs) / n,
            "win_acc": win_correct / win_total if win_total else None,
            "brier": sum(brier_scores) / len(brier_scores) if brier_scores else None,
            "over85_acc": over85_correct / over85_total if over85_total else None,
        }

    if not results:
        print("No results to compare.")
        return

    COL = 13  # width of each version column
    LABELS = {"poisson_v2": "v2", "poisson_v3_bullpen": "v3_bullpen", "poisson_v4_lineup": "v4_lineup"}
    header_cols = "".join(f"{LABELS.get(v, v):>{COL}}" for v in VERSIONS)
    sep = "=" * (32 + COL * len(VERSIONS))
    print("\n" + sep)
    print(f"{'Metric':<30}  {header_cols}")
    print(sep)

    def _fmt(val, fmt):
        return f"{val:{fmt}}" if val is not None else "—"

    def row(label, key, fmt=".3f", lower_better=True):
        vals = [results.get(v, {}).get(key) for v in VERSIONS]
        cells = "".join(f"{_fmt(v, fmt):>{COL}}" for v in vals)
        # Mark the best version
        actuals = [(v, i) for i, v in enumerate(vals) if v is not None]
        best_mark = ""
        if len(actuals) >= 2:
            best_i = min(actuals, key=lambda x: x[0] if lower_better else -x[0])[1]
            best_mark = f"  ← {LABELS.get(VERSIONS[best_i], VERSIONS[best_i])} best"
        print(f"  {label:<28}  {cells}{best_mark}")

    counts = "".join(f"{results.get(v, {}).get('n', 0):>{COL}}" for v in VERSIONS)
    print(f"  {'Games matched':<28}  {counts}")
    row("MAE home xRuns (↓ better)", "mae_home_xr")
    row("MAE away xRuns (↓ better)", "mae_away_xr")
    row("MAE total xRuns (↓ better)", "mae_total_xr")
    row("Bias total (0 = perfect)", "bias_total")
    row("Win accuracy (↑ better)", "win_acc", ".3f", lower_better=False)
    row("Brier score (↓ better)", "brier", ".4f")
    row("Over 8.5 accuracy (↑ better)", "over85_acc", ".3f", lower_better=False)
    print(sep)

    # Summary verdict: compare each shadow vs v2 on total MAE
    n2 = results.get(V2, {}).get("n", 0)
    mae_v2 = results.get(V2, {}).get("mae_total_xr")
    if mae_v2 is not None:
        print()
        for ver, label in [(V3, "v3"), (V4, "v4")]:
            if ver not in results:
                continue
            mae_ver = results[ver]["mae_total_xr"]
            delta = mae_v2 - mae_ver
            if delta > 0.02:
                verdict = f"{label} IMPROVES MAE by {delta:.3f} runs/game"
            elif delta < -0.02:
                verdict = f"v2 BETTER (MAE delta={delta:.3f})"
            else:
                verdict = f"WASH (MAE delta={delta:.3f}) — need more data"
            print(f"  v2 vs {label}: {verdict}")
        print(f"  (n={n2} game samples — aim for 200+ before deciding)")


if __name__ == "__main__":
    main()
