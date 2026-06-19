"""
Compare poisson_v2 (starter-only blend) vs poisson_v3_bullpen (explicit starter/bullpen split).

Joins mlb_run_predictions for both versions against finished games with actual scores.
Prints per-version: MAE for xRuns, win-prediction accuracy, Brier score, and O/U accuracy.

Run AFTER several weeks of data have accumulated in both versions:
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

    # Load predictions for both versions
    preds = (
        supabase.table("mlb_run_predictions")
        .select("*")
        .in_("model_version", [V2, V3])
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
    for ver in [V2, V3]:
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

    print("\n" + "=" * 65)
    print(f"{'Metric':<30} {'poisson_v2':>15} {'v3_bullpen':>15}")
    print("=" * 65)

    def row(label, key, fmt=".3f"):
        v2 = results.get(V2, {}).get(key)
        v3 = results.get(V3, {}).get(key)
        v2s = f"{v2:{fmt}}" if v2 is not None else "—"
        v3s = f"{v3:{fmt}}" if v3 is not None else "—"
        winner = ""
        if v2 is not None and v3 is not None:
            # Lower is better for MAE/Brier; higher is better for accuracy
            if key in ("win_acc", "over85_acc"):
                winner = " ← v3 better" if v3 > v2 else (" ← v2 better" if v2 > v3 else "")
            else:
                winner = " ← v3 better" if v3 < v2 else (" ← v2 better" if v2 < v3 else "")
        print(f"  {label:<28} {v2s:>15} {v3s:>15}{winner}")

    n2 = results.get(V2, {}).get("n", 0)
    n3 = results.get(V3, {}).get("n", 0)
    print(f"  {'Games matched':<28} {n2:>15} {n3:>15}")
    row("MAE home xRuns (↓ better)", "mae_home_xr")
    row("MAE away xRuns (↓ better)", "mae_away_xr")
    row("MAE total xRuns (↓ better)", "mae_total_xr")
    row("Bias total (0 = perfect)", "bias_total")
    row("Win accuracy (↑ better)", "win_acc", ".3f")
    row("Brier score (↓ better)", "brier", ".4f")
    row("Over 8.5 accuracy (↑ better)", "over85_acc", ".3f")
    print("=" * 65)

    if V2 in results and V3 in results:
        mae_v2 = results[V2]["mae_total_xr"]
        mae_v3 = results[V3]["mae_total_xr"]
        delta = mae_v2 - mae_v3
        verdict = (
            f"v3 IMPROVES MAE by {delta:.3f} runs/game — keep bullpen"
            if delta > 0.02
            else f"v2 BETTER or equivalent (MAE delta={delta:.3f}) — hold on bullpen"
            if delta < -0.02
            else f"WASH (MAE delta={delta:.3f}) — need more data"
        )
        print(f"\n  Verdict: {verdict}")
        print(f"  (n={n2} game samples — aim for 200+ before deciding)")


if __name__ == "__main__":
    main()
