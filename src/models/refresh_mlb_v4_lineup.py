"""
Hourly v4 lineup refresh.

After sync_mlb_lineups confirms batting orders for games starting in the next
2 hours, this script recomputes poisson_v4_lineup predictions and the
corresponding mlb_model_picks entry for exactly those games.

Cost:
  - Odds API credits: 0  (reads mlb_odds from Supabase, already there from the
    morning full-engine run; no per-event or bulk Odds API call issued here)
  - External HTTP: 0  (all inputs already in Supabase from morning + lineup sync)
  - v2/v3/v5/v6/v7 are untouched — their inputs don't change intraday
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.models.generate_mlb_run_predictions import (
    FALLBACK_LEAGUE_AVG,
    HOME_ADV,
    MODEL_VERSION_LU,
    _lineup_offense_factor,
    _safe,
    build_bullpen_strength,
    build_lineup_data,
    build_pitcher_adjustments,
    build_run_matrix,
    build_strengths,
    compute_xr_v4,
    markets_from_matrix,
)
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

WINDOW_HOURS = 2
SPORT_KEY = "baseball_mlb"
TORONTO = ZoneInfo("America/Toronto")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _window_games():
    """
    Return games (id, home_team_name, away_team_name) whose first pitch is
    between now and now+WINDOW_HOURS — matching the lineup-sync time gate.
    """
    now_utc = datetime.now(ZoneInfo("UTC"))
    window_close = now_utc + timedelta(hours=WINDOW_HOURS)
    today = now_utc.astimezone(TORONTO).date()

    rows = (
        supabase.table("games")
        .select("id,home_team_name,away_team_name,start_time_utc,game_date")
        .eq("sport_key", SPORT_KEY)
        .gte("game_date", today.isoformat())
        .lte("game_date", (today + timedelta(days=1)).isoformat())
        .execute()
        .data
    )

    in_window = []
    for g in rows:
        st = g.get("start_time_utc")
        if not st:
            continue
        try:
            game_start = datetime.fromisoformat(str(st).replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if now_utc < game_start <= window_close:
            in_window.append(g)
    return in_window


def _compute_v4_predictions(games):
    """Compute and upsert poisson_v4_lineup for the given game list."""
    if not games:
        return 0

    today = datetime.now(TORONTO).date()

    strengths = build_strengths()
    league_avgs = [r["league_avg_runs"] for r in strengths.values() if r.get("league_avg_runs")]
    league_avg = (sum(league_avgs) / len(league_avgs)) if league_avgs else FALLBACK_LEAGUE_AVG

    pitchers = build_pitcher_adjustments()
    bullpens = build_bullpen_strength()

    if not bullpens:
        print("  ⚠ No bullpen data — v4 requires v3 defense; skipping v4 refresh")
        return 0

    batter_splits, game_lineups, pitcher_hands = build_lineup_data(today)

    saved = 0
    for g in games:
        gid = g["id"]
        home = g["home_team_name"]
        away = g["away_team_name"]

        hs = strengths.get(home)
        as_ = strengths.get(away)
        h_score = _safe(hs["shrunk_scoring_index"] if hs else None, 1.0)
        h_allow = _safe(hs["shrunk_allowed_index"] if hs else None, 1.0)
        a_score = _safe(as_["shrunk_scoring_index"] if as_ else None, 1.0)
        a_allow = _safe(as_["shrunk_allowed_index"] if as_ else None, 1.0)

        home_pitcher = pitchers.get((gid, "home"))
        away_pitcher = pitchers.get((gid, "away"))
        home_bp = bullpens.get(home)
        away_bp = bullpens.get(away)

        home_off = _lineup_offense_factor(
            gid, "home", "away", batter_splits, game_lineups, pitcher_hands
        )
        away_off = _lineup_offense_factor(
            gid, "away", "home", batter_splits, game_lineups, pitcher_hands
        )

        if home_off is None and away_off is None:
            print(f"  ⏳ {away} @ {home}: no confirmed lineup yet — skipping v4 refresh")
            continue

        home_xr, away_xr = compute_xr_v4(
            home_pitcher, away_pitcher, home_bp, away_bp,
            h_score, a_score, h_allow, a_allow, league_avg,
            home_off_factor=home_off,
            away_off_factor=away_off,
        )

        m = markets_from_matrix(build_run_matrix(home_xr, away_xr), home_xr, away_xr)

        row = {
            "game_id": gid,
            "model_version": MODEL_VERSION_LU,
            "home_team_name": home,
            "away_team_name": away,
            "expected_home_runs": round(home_xr, 3),
            "expected_away_runs": round(away_xr, 3),
            "expected_total_runs": round(home_xr + away_xr, 3),
            **m,
        }
        supabase.table("mlb_run_predictions").upsert(
            row, on_conflict="game_id,model_version"
        ).execute()

        h_str = f"{home_off:.3f}" if home_off is not None else "avg"
        a_str = f"{away_off:.3f}" if away_off is not None else "avg"
        print(
            f"  v4 {away} @ {home}: "
            f"xR {home_xr:.2f}-{away_xr:.2f} | "
            f"LU off: {home}={h_str} {away}={a_str}"
        )
        saved += 1

    return saved


def _refresh_v4_picks(game_ids):
    """
    Regenerate mlb_model_picks for poisson_v4_lineup on the given game_ids.
    Reads predictions from Supabase (just upserted) and odds from mlb_odds
    (Supabase, written at morning full-run time — no Odds API call).
    """
    if not game_ids:
        return 0

    preds_raw = (
        supabase.table("mlb_run_predictions")
        .select("*")
        .eq("model_version", MODEL_VERSION_LU)
        .in_("game_id", list(game_ids))
        .execute()
        .data
    )

    saved = 0
    for pred in preds_raw:
        gid = pred["game_id"]
        home = pred["home_team_name"]
        away = pred["away_team_name"]

        all_cands = (
            _ml_candidates(pred, home, away)
            + _totals_candidates(pred)
            + _runline_candidates(pred, home, away)
        )
        if not all_cands:
            continue

        all_cands.sort(key=lambda c: c["raw_confidence"], reverse=True)
        best = all_cands[0]
        cal_conf = _shrink(best["raw_confidence"])

        odds_rows = _get_odds_rows(gid)
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
            "model_version": MODEL_VERSION_LU,
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
        saved += 1

    return saved


def main():
    games = _window_games()

    if not games:
        print("No games in the 2-hour window — nothing to refresh.")
        print("✅ MLB v4 lineup refresh: 0 games")
        return

    print(f"  {len(games)} game(s) in 2-hour window: "
          + ", ".join(f"{g['away_team_name']} @ {g['home_team_name']}" for g in games))

    saved_preds = _compute_v4_predictions(games)

    refreshed_game_ids = {g["id"] for g in games}
    saved_picks = _refresh_v4_picks(refreshed_game_ids)

    print(
        f"\n✅ MLB v4 lineup refresh: "
        f"{saved_preds} predictions updated | {saved_picks} picks updated"
    )


if __name__ == "__main__":
    main()
