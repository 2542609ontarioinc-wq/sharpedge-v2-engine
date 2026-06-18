"""
Backtest the MLB Poisson model against settled game results.

Reads all finished MLB games that have run predictions and evaluates:
  - Moneyline (home / away)
  - Totals Over/Under at 7.5, 8.5, 9.5
  - Run-line home -1.5 (home wins by 2+)

Prints accuracy per market and ROI assuming standard -110 juice (~1.909 decimal)
unless real odds are available in mlb_odds.

Writes results to mlb_backtest_results (insert, not upsert — each run is
a fresh snapshot; query by max(run_date) for the latest figures).
"""
from collections import defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"
MODEL_VERSION = "poisson_v2"
JUICE_DECIMAL = 1.909       # -110 standard American line ≈ 1/0.524
FINISHED_STATUSES = {"ft", "aot", "post", "f", "final", "game finished"}


def _num(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _is_finished(g):
    return (
        (g.get("status") or "").lower() in FINISHED_STATUSES
        or (g.get("period") or "").lower() in FINISHED_STATUSES
    )


def _avg_ml_odds(odds_rows, team_name):
    """Return average decimal odds for this team's moneyline across all books."""
    matches = [
        _num(o["odds_decimal"])
        for o in odds_rows
        if (o.get("market") or "").lower() == "h2h"
        and (o.get("selection") or "").lower() == team_name.lower()
        and _num(o.get("odds_decimal")) > 1.0
    ]
    return sum(matches) / len(matches) if matches else JUICE_DECIMAL


def _avg_totals_odds(odds_rows, side, line):
    matches = [
        _num(o["odds_decimal"])
        for o in odds_rows
        if (o.get("market") or "").lower() == "totals"
        and (o.get("selection") or "").lower() == side
        and _num(o.get("line")) == line
        and _num(o.get("odds_decimal")) > 1.0
    ]
    return sum(matches) / len(matches) if matches else JUICE_DECIMAL


def main():
    print("Loading finished MLB games...")
    games = (
        supabase.table("games")
        .select("*")
        .eq("sport_key", SPORT_KEY)
        .execute()
        .data
    )
    finished = {g["id"]: g for g in games if _is_finished(g)}
    print(f"  Finished games found: {len(finished)}")

    if not finished:
        print("No finished games to backtest.")
        return

    preds = (
        supabase.table("mlb_run_predictions")
        .select("*")
        .eq("model_version", MODEL_VERSION)
        .execute()
        .data
    )
    pred_map = {p["game_id"]: p for p in preds}

    odds_map = defaultdict(list)
    all_odds = supabase.table("mlb_odds").select("*").execute().data
    for o in all_odds:
        if o.get("game_id"):
            odds_map[o["game_id"]].append(o)

    # accumulators: {market_key: {"correct": int, "total": int, "roi_sum": float}}
    results = defaultdict(lambda: {"correct": 0, "total": 0, "roi": 0.0, "line": None})

    matched = 0
    for gid, game in finished.items():
        pred = pred_map.get(gid)
        if not pred:
            continue
        matched += 1

        hs = _num(game.get("home_score"))
        as_ = _num(game.get("away_score"))
        total = hs + as_
        diff = hs - as_

        home = game["home_team_name"]
        away = game["away_team_name"]
        o_rows = odds_map.get(gid, [])

        # --- MONEYLINE ---
        pred_home_win = _num(pred.get("home_win_probability")) > 50
        ml_key = "moneyline"
        results[ml_key]["total"] += 1
        results[ml_key]["line"] = None
        if pred_home_win:
            correct = hs > as_
            odds_used = _avg_ml_odds(o_rows, home)
        else:
            correct = as_ > hs
            odds_used = _avg_ml_odds(o_rows, away)
        results[ml_key]["correct"] += int(correct)
        results[ml_key]["roi"] += (odds_used - 1) if correct else -1.0

        # --- TOTALS ---
        for line, ov_key in [(7.5, "over_75_probability"), (8.5, "over_85_probability"), (9.5, "over_95_probability")]:
            key = f"total_{'%.1f' % line}"
            results[key]["total"] += 1
            results[key]["line"] = line
            ov_prob = _num(pred.get(ov_key))
            if ov_prob > 50:
                correct = total > line
                odds_used = _avg_totals_odds(o_rows, "over", line)
            else:
                correct = total <= line
                odds_used = _avg_totals_odds(o_rows, "under", line)
            results[key]["correct"] += int(correct)
            results[key]["roi"] += (odds_used - 1) if correct else -1.0

        # --- RUN LINE home -1.5 ---
        rl_key = "run_line_home_-1.5"
        results[rl_key]["total"] += 1
        results[rl_key]["line"] = -1.5
        h_m15_prob = _num(pred.get("home_rl_minus15_prob"))
        if h_m15_prob > 50:
            correct = diff >= 2
            odds_used = JUICE_DECIMAL
        else:
            correct = diff < 2
            odds_used = JUICE_DECIMAL
        results[rl_key]["correct"] += int(correct)
        results[rl_key]["roi"] += (odds_used - 1) if correct else -1.0

    print(f"\n  Games matched with predictions: {matched}")
    print("\n{'Market':<30} {'Total':>6} {'Correct':>8} {'Accuracy':>9} {'ROI/bet':>9}")
    print("-" * 66)

    today = date.today().isoformat()
    rows_to_save = []

    for mkt, r in sorted(results.items()):
        total = r["total"]
        correct = r["correct"]
        if total == 0:
            continue
        acc = round(correct / total * 100, 1)
        roi = round(r["roi"] / total * 100, 2)
        print(f"  {mkt:<28} {total:>6} {correct:>8} {acc:>8.1f}% {roi:>8.2f}%")
        rows_to_save.append({
            "run_date": today,
            "market": mkt,
            "line": r["line"],
            "total_predictions": total,
            "correct": correct,
            "incorrect": total - correct,
            "accuracy": acc,
            "avg_odds_decimal": JUICE_DECIMAL,
            "roi": roi,
            "notes": f"Model={MODEL_VERSION}",
        })

    if rows_to_save:
        supabase.table("mlb_backtest_results").insert(rows_to_save).execute()
        print(f"\n✅ Backtest results saved: {len(rows_to_save)} market rows (run_date={today})")
    else:
        print("\nNo backtest rows to save.")


if __name__ == "__main__":
    main()
