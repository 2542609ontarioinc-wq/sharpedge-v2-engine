"""
Generate picks for all MLB model versions (v2–v7) for model comparison.

Reads mlb_run_predictions for every version and applies the SAME honest pick
logic as build_mlb_final_picks.py: calibration, no-vig edge, REAL/suspect/no-odds
flags, market anchoring.  Writes to mlb_model_picks tagged with model_version.

Does NOT touch mlb_final_predictions or mlb_safe_zone — those remain v2 production.

Extra API/compute cost: zero external calls.  Odds are fetched once per game
and shared across versions.  Compute is pure Python on already-stored predictions.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.models.build_mlb_final_picks import (
    _best_odds_decimal,
    _get_odds_rows,
    _ml_candidates,
    _num,
    _resolve_novig,
    _runline_candidates,
    _safe_zone_picks,
    _shrink,
    _totals_candidates,
)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

VERSIONS = [
    "poisson_v2",
    "poisson_v3_bullpen",
    "poisson_v4_lineup",
    "poisson_v5_environment",
    "poisson_v6_form",
    "poisson_v7_statcast",
]


def main():
    preds_raw = (
        supabase.table("mlb_run_predictions")
        .select("*")
        .in_("model_version", VERSIONS)
        .execute()
        .data
    )

    # One prediction per (version, game_id) — upsert table, so no duplicates
    by_version = {}
    for p in preds_raw:
        ver = p.get("model_version")
        gid = p.get("game_id")
        if ver and gid:
            by_version.setdefault(ver, {})[gid] = p

    # Collect all game ids and fetch odds once — shared across all model versions
    all_game_ids = {gid for ver_dict in by_version.values() for gid in ver_dict}
    odds_by_game = {gid: _get_odds_rows(gid) for gid in all_game_ids}

    saved_total = 0
    skipped = 0

    for ver in VERSIONS:
        ver_preds = by_version.get(ver, {})
        saved_ver = 0

        for gid, pred in ver_preds.items():
            home = pred["home_team_name"]
            away = pred["away_team_name"]

            all_cands = (
                _ml_candidates(pred, home, away)
                + _totals_candidates(pred)
                + _runline_candidates(pred, home, away)
            )

            if not all_cands:
                skipped += 1
                continue

            all_cands.sort(key=lambda c: c["raw_confidence"], reverse=True)
            best = all_cands[0]
            cal_conf = _shrink(best["raw_confidence"])

            odds_rows = odds_by_game.get(gid, [])
            novig_result = _resolve_novig(odds_rows, best["market"], best["pick"])

            if novig_result:
                novig_pct, pick_odds = novig_result
                edge = round(cal_conf - novig_pct, 2)
                flag = "REAL" if -10 <= edge <= 15 else "suspect"
                book_odds = pick_odds
            else:
                novig_pct = pick_odds = edge = None
                flag = "no-odds"
                book_odds, _ = _best_odds_decimal(odds_rows, best["market"], best["pick"])

            am_odds = None
            if book_odds and book_odds > 1:
                if book_odds >= 2:
                    am_odds = int((book_odds - 1) * 100)
                else:
                    am_odds = int(-100 / (book_odds - 1))

            bal_pick, bal_prob, _, _ = _safe_zone_picks(
                best["market"], best["pick"], pred, home, away
            )

            row = {
                "game_id": gid,
                "model_version": ver,
                "home_team_name": home,
                "away_team_name": away,
                "best_pick": best["pick"],
                "market": best["market"],
                "raw_confidence": best["raw_confidence"],
                "calibrated_confidence": cal_conf,
                "odds_decimal": book_odds,
                "odds_american": am_odds,
                "market_implied_probability": novig_pct,
                "model_edge": edge,
                "edge_flag": flag,
                "balanced_pick": bal_pick,
                "balanced_prob": round(bal_prob, 2) if bal_prob is not None else None,
                "updated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
            }

            supabase.table("mlb_model_picks").upsert(
                row, on_conflict="game_id,model_version"
            ).execute()
            saved_ver += 1

        saved_total += saved_ver
        print(f"  {ver}: {saved_ver} picks")

    print(f"\n✅ MLB model picks saved: {saved_total} across {len(VERSIONS)} versions | skipped: {skipped}")


if __name__ == "__main__":
    main()
