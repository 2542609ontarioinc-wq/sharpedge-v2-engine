"""
Build mlb_pick_detail: enriched per-pick diagnostic row for every graded game pick.

Joins:
  mlb_pick_grades       — grade, units, confidence, odds, actual scores
  games                 — game_date
  mlb_run_predictions   — model projections (prefers v4_lineup → v7 → v2)
  mlb_clv_tracking      — closing-line value

DIAGNOSTIC ONLY — does not touch any prediction or pick table.
Run after grade_mlb_picks.
"""
import re
from datetime import datetime, timezone

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.grading.subscriber_thresholds import (
    EDGE_MIN, PROB_MIN, BOTD_EDGE, BOTD_PROB, EDGE_MAX,
)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"

# Preferred model version for projections — first one found in preds_by_game wins.
PREF_VERSIONS = [
    "poisson_v4_lineup",
    "poisson_v7_statcast",
    "poisson_v6_form",
    "poisson_v5_environment",
    "poisson_v3_bullpen",
    "poisson_v2",
]


def _num(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _edge_bucket(edge):
    if edge is None:
        return None
    e = abs(float(edge))
    if e < 2.0:
        return "<2%"
    if e < 5.0:
        return "2-5%"
    return "5%+"


def _conf_bucket(conf):
    """conf is on the 50–100 percentage scale."""
    if conf is None:
        return None
    c = float(conf)
    if c < 55.0:
        return "<55%"
    if c < 65.0:
        return "55-65%"
    if c < 75.0:
        return "65-75%"
    return "75%+"


def _match_team(pick_fragment, home, away):
    """
    Return 'home', 'away', or None.
    Uses exact then last-word then containment heuristics.
    """
    def norm(s):
        return (s or "").lower().strip()

    p = norm(pick_fragment)
    h = norm(home)
    a = norm(away)
    if not p:
        return None
    if p == h or p in h or h in p:
        return "home"
    if p == a or p in a or a in p:
        return "away"
    # last word (city or nickname)
    p_last = p.split()[-1] if p.split() else ""
    if p_last and p_last == (h.split()[-1] if h.split() else ""):
        return "home"
    if p_last and p_last == (a.split()[-1] if a.split() else ""):
        return "away"
    return None


def _parse_pick(market, pick_str, home, away):
    """
    Returns (pick_side, pick_line, is_over, is_home_pick).
    pick_side: 'home'|'away'|'over'|'under' or None
    pick_line: numeric threshold (line value), or None
    is_over:   True/False for totals-type picks, else None
    is_home_pick: True/False for team-based picks, else None
    """
    mkt = (market or "").lower()
    p = (pick_str or "").strip()
    pl = p.lower()

    # ── Totals: "Over 8.5" / "Under 7.5" ──────────────────────────────────
    mat = re.match(r"^(over|under)\s+([\d.]+)$", pl)
    if mat:
        side = mat.group(1)
        line = float(mat.group(2))
        return side, line, (side == "over"), None

    # ── Moneyline: pick is the team name ───────────────────────────────────
    if mkt == "moneyline":
        team_side = _match_team(p, home, away)
        side = team_side  # 'home' or 'away'
        is_home = (team_side == "home") if team_side else None
        return side, None, None, is_home

    # ── Run line: "Team Name -1.5" ─────────────────────────────────────────
    if mkt == "run_line":
        parts = p.rsplit(None, 1)
        if len(parts) == 2:
            try:
                line = float(parts[1])
                team_side = _match_team(parts[0].strip(), home, away)
                side = team_side
                is_home = (team_side == "home") if team_side else None
                return side, line, None, is_home
            except ValueError:
                pass
        return None, None, None, None

    # ── Safe zone picks: various formats ───────────────────────────────────
    if mkt in ("safe_balanced", "safe_banker"):
        # "Team moneyline"
        if pl.endswith(" moneyline"):
            team = p[: -len(" moneyline")].strip()
            team_side = _match_team(team, home, away)
            is_home = (team_side == "home") if team_side else None
            return team_side, None, None, is_home

        # "Team +/-X.X" (run-line safe)
        parts = p.rsplit(None, 1)
        if len(parts) == 2:
            try:
                line = float(parts[1])
                team_side = _match_team(parts[0].strip(), home, away)
                is_home = (team_side == "home") if team_side else None
                return team_side, line, None, is_home
            except ValueError:
                pass

    return None, None, None, None


def _sub_flags_sharp(edge_flag, model_edge, calibrated_conf):
    """Return (subscriber_qualified, bet_of_day) for a sharp pick row."""
    if edge_flag != "REAL":
        return False, False
    if model_edge is None or calibrated_conf is None:
        return False, False
    edge = float(model_edge)
    prob = float(calibrated_conf)
    if not (EDGE_MIN <= edge <= EDGE_MAX and prob >= PROB_MIN):
        return False, False
    botd = edge >= BOTD_EDGE and prob >= BOTD_PROB
    return True, botd


def _sub_flags_safe(safe_prob):
    """Return (subscriber_qualified, bet_of_day) for a safe-zone pick row.
    Safe-zone picks carry no model edge so they can never be Bet of the Day.
    """
    if safe_prob is None:
        return False, False
    return float(safe_prob) >= PROB_MIN, False


def main():
    grades = supabase.table("mlb_pick_grades").select("*").execute().data

    # Safe-zone probability lookup: (game_id, 'safe_balanced'|'safe_banker') → prob
    safe_rows = supabase.table("mlb_safe_zone").select(
        "game_id,balanced_prob,banker_prob"
    ).execute().data
    safe_probs: dict[tuple, float | None] = {}
    for sz in safe_rows:
        gid = sz["game_id"]
        safe_probs[(gid, "safe_balanced")] = _num(sz.get("balanced_prob"))
        safe_probs[(gid, "safe_banker")]   = _num(sz.get("banker_prob"))

    games_data = (
        supabase.table("games")
        .select("id,game_date")
        .eq("sport_key", SPORT_KEY)
        .execute()
        .data
    )
    game_dates = {g["id"]: g.get("game_date") for g in games_data}

    # Run predictions keyed by game_id → {model_version: row}
    preds_raw = (
        supabase.table("mlb_run_predictions")
        .select(
            "game_id,model_version,expected_home_runs,"
            "expected_away_runs,expected_total_runs"
        )
        .execute()
        .data
    )
    preds_by_game: dict[str, dict[str, dict]] = {}
    for p in preds_raw:
        gid = p["game_id"]
        ver = p.get("model_version", "")
        preds_by_game.setdefault(gid, {})[ver] = p

    # CLV keyed by (game_id, market, pick)
    clv_raw = (
        supabase.table("mlb_clv_tracking")
        .select("game_id,market,pick,clv,beat_close")
        .execute()
        .data
    )
    clv_map = {(r["game_id"], r["market"], r["pick"]): r for r in clv_raw}

    now = datetime.now(timezone.utc).isoformat()
    saved = 0

    for gr in grades:
        gid = gr.get("game_id")
        if not gid:
            continue

        market = (gr.get("market") or "").lower()
        pick_str = gr.get("pick") or ""
        home = gr.get("home_team_name") or ""
        away = gr.get("away_team_name") or ""

        hs = gr.get("home_score")
        as_ = gr.get("away_score")
        actual_total = (int(hs) + int(as_) if hs is not None and as_ is not None else None)
        actual_diff  = (int(hs) - int(as_) if hs is not None and as_ is not None else None)

        pick_side, pick_line, is_over, is_home_pick = _parse_pick(
            market, pick_str, home, away
        )

        odds = _num(gr.get("odds_decimal"))
        is_favorite = (True if odds is not None and odds < 2.0 else
                       False if odds is not None else None)

        # Best available prediction for this game
        game_preds = preds_by_game.get(gid, {})
        best_pred = next(
            (game_preds[v] for v in PREF_VERSIONS if v in game_preds), None
        )
        model_proj_total = _num(best_pred.get("expected_total_runs") if best_pred else None)
        model_proj_home  = _num(best_pred.get("expected_home_runs")  if best_pred else None)
        model_proj_away  = _num(best_pred.get("expected_away_runs")  if best_pred else None)

        total_bias = None
        if model_proj_total is not None and actual_total is not None:
            total_bias = round(model_proj_total - actual_total, 3)

        calib_conf = _num(gr.get("calibrated_confidence"))
        raw_conf   = _num(gr.get("raw_confidence"))
        model_edge = _num(gr.get("model_edge"))

        clv_row    = clv_map.get((gid, market, pick_str))
        clv        = _num(clv_row.get("clv") if clv_row else None)
        beat_close = (clv_row.get("beat_close") if clv_row else None)

        # Subscriber qualification flags
        if market in ("safe_balanced", "safe_banker"):
            sub_qual, botd = _sub_flags_safe(safe_probs.get((gid, market)))
        else:
            sub_qual, botd = _sub_flags_sharp(
                gr.get("edge_flag"), model_edge, calib_conf
            )

        row = {
            "game_id":        gid,
            "game_date":      game_dates.get(gid),
            "home_team":      home,
            "away_team":      away,
            "market":         market,
            "pick":           pick_str,
            "pick_line":      pick_line,
            "pick_side":      pick_side,
            "is_home_pick":   is_home_pick,
            "is_over":        is_over,
            "is_favorite":    is_favorite,
            "model_proj_total": model_proj_total,
            "model_proj_home":  model_proj_home,
            "model_proj_away":  model_proj_away,
            "calibrated_conf":  calib_conf,
            "raw_confidence":   raw_conf,
            "model_edge":       model_edge,
            "edge_bucket":      _edge_bucket(model_edge),
            "conf_bucket":      _conf_bucket(calib_conf),
            "odds_decimal":     odds,
            "edge_flag":        gr.get("edge_flag"),
            "no_odds":          gr.get("no_odds", False),
            "home_score":       hs,
            "away_score":       as_,
            "actual_total":     actual_total,
            "actual_diff":      actual_diff,
            "total_bias":       total_bias,
            "grade":            gr.get("grade"),
            "units_result":     _num(gr.get("units_result")),
            "roi_percent":      _num(gr.get("roi_percent")),
            "clv":                  clv,
            "beat_close":           beat_close,
            "subscriber_qualified": sub_qual,
            "bet_of_day":           botd,
            "graded_at":            gr.get("graded_at") or now,
        }

        supabase.table("mlb_pick_detail").upsert(
            row, on_conflict="game_id,market,pick"
        ).execute()
        saved += 1

    print(f"✅ MLB pick detail built: {saved} rows")


if __name__ == "__main__":
    main()
