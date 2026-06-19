"""
Grade settled MLB picks against actual game results.

Reads from:
  mlb_final_predictions  — sharp picks (moneyline / totals / run_line)
  mlb_safe_zone          — balanced + banker safe-zone picks
  games                  — actual home/away scores once status = finished

Writes per-pick rows to mlb_pick_grades (upsert on game_id, market, pick).

Honesty rules:
  - no_odds picks: WIN counts as break-even (0 units), LOSS costs -1 unit.
  - VOID picks contribute 0 units and are excluded from win-rate.
  - Safe-zone odds are used when stored; otherwise break-even.
"""
import re
from datetime import datetime, timezone

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"
FINISHED_STATUSES = {"ft", "aot", "post", "f", "final", "game finished", "finished"}

# Bidirectional team name/abbreviation aliases.
# Maps every known form → one canonical key so both sides of a comparison
# resolve identically regardless of which API or pick-generation path produced
# the name (e.g. OAK vs ATH after the A's relocation, ARI vs AZ, etc.).
_TEAM_ALIASES: dict[str, str] = {
    # Athletics: moved from Oakland; some books/APIs still use OAK
    "oak": "ath", "ath": "ath",
    "oakland athletics": "ath", "sacramento athletics": "ath", "athletics": "ath",
    # Diamondbacks: MLB Stats API uses "AZ", most others use "ARI"
    "ari": "az", "az": "az", "arizona diamondbacks": "az",
    # Nationals: WAS (our data) vs WSH (MLB API)
    "was": "wsh", "wsh": "wsh", "washington nationals": "wsh",
    # Giants: SFG (Retrosheet/some APIs) vs SF
    "sfg": "sf", "sf": "sf", "san francisco giants": "sf",
    # White Sox: CHW (baseball-reference) vs CWS (odds APIs)
    "chw": "cws", "cws": "cws", "chicago white sox": "cws",
}


def _team_key(name: str) -> str:
    n = (name or "").lower().strip()
    return _TEAM_ALIASES.get(n, n)


def _teams_match(a: str, b: str) -> bool:
    return _team_key(a) == _team_key(b)


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _is_finished(g):
    status = (g.get("status") or "").lower()
    period = (g.get("period") or "").lower()
    return status in FINISHED_STATUSES or period in FINISHED_STATUSES


# ---------------------------------------------------------------------------
# Graders
# ---------------------------------------------------------------------------

def grade_mlb_pick(market, pick, home, away, home_score, away_score):
    """
    Grade a sharp MLB pick.  Returns 'WIN', 'LOSS', or 'VOID'.

    market: 'moneyline' | 'totals' | 'run_line'
    pick:   team name  | 'Over 8.5' / 'Under 7.5'  | 'New York Yankees -1.5'
    """
    total = home_score + away_score
    diff = home_score - away_score
    m = (market or "").lower().strip()
    p = (pick or "").strip()
    pl = p.lower()

    if m == "moneyline":
        winner = home if home_score > away_score else away
        return "WIN" if _teams_match(pl, winner) else "LOSS"

    if m == "totals":
        mat = re.match(r"^(over|under)\s+([\d.]+)$", pl)
        if not mat:
            return "VOID"
        direction, line = mat.group(1), float(mat.group(2))
        return "WIN" if (total > line if direction == "over" else total < line) else "LOSS"

    if m == "run_line":
        # e.g. "New York Yankees -1.5"
        parts = p.rsplit(None, 1)
        if len(parts) != 2:
            return "VOID"
        team, line_str = parts
        try:
            line = float(line_str)
        except ValueError:
            return "VOID"
        if _teams_match(team, home):
            team_margin = diff
        elif _teams_match(team, away):
            team_margin = -diff
        else:
            return "VOID"
        # covers when team_margin + handicap > 0
        # e.g. -1.5: team must win by 2+ → team_margin > 1.5
        return "WIN" if team_margin + line > 0 else "LOSS"

    return "VOID"


def grade_mlb_safe_zone_pick(pick, home, away, home_score, away_score):
    """
    Grade a safe-zone pick.  Handles three formats:
      'Over 7.5' / 'Under 10.5'  — adjusted total
      'Boston Red Sox +1.5'       — run-line step-back
      'Boston Red Sox moneyline'  — moneyline step-back (from run_line sharp)
    """
    total = home_score + away_score
    diff = home_score - away_score
    p = (pick or "").strip()
    pl = p.lower()

    # Over/Under
    mat = re.match(r"^(over|under)\s+([\d.]+)$", pl)
    if mat:
        direction, line = mat.group(1), float(mat.group(2))
        return "WIN" if (total > line if direction == "over" else total < line) else "LOSS"

    # "{Team} moneyline"
    if pl.endswith(" moneyline"):
        team = p[: -len(" moneyline")].strip()
        winner = home if home_score > away_score else away
        return "WIN" if _teams_match(team, winner) else "LOSS"

    # "{Team} +1.5" / "{Team} +2.5"
    parts = p.rsplit(None, 1)
    if len(parts) == 2:
        team, line_str = parts
        try:
            line = float(line_str)
        except ValueError:
            return "VOID"
        if _teams_match(team, home):
            team_margin = diff
        elif _teams_match(team, away):
            team_margin = -diff
        else:
            return "VOID"
        return "WIN" if team_margin + line > 0 else "LOSS"

    return "VOID"


def units_result(grade, odds_decimal, no_odds=False):
    """
    WIN  + real odds → odds_decimal - 1
    WIN  + no_odds   → 0.0  (break-even; can't calculate profit without price)
    LOSS             → -1.0
    VOID             → 0.0
    """
    if grade == "VOID":
        return 0.0
    if grade == "LOSS":
        return -1.0
    # WIN
    if no_odds or odds_decimal is None or odds_decimal <= 1.0:
        return 0.0
    return round(float(odds_decimal) - 1.0, 2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    games = (
        supabase.table("games")
        .select("id,home_team_name,away_team_name,home_score,away_score,status,period")
        .eq("sport_key", SPORT_KEY)
        .execute()
        .data
    )
    finished = {g["id"]: g for g in games if _is_finished(g)}

    now = datetime.now(timezone.utc).isoformat()
    saved = 0

    # === Sharp picks ===
    preds = supabase.table("mlb_final_predictions").select("*").execute().data

    for pred in preds:
        gid = pred.get("game_id")
        game = finished.get(gid)
        if not game:
            continue

        hs = int(_num(game.get("home_score")))
        as_ = int(_num(game.get("away_score")))
        home = game["home_team_name"]
        away = game["away_team_name"]

        grade = grade_mlb_pick(
            pred.get("market"), pred.get("best_pick"), home, away, hs, as_
        )

        no_odds = (pred.get("edge_flag") or "") == "no-odds"
        odds = _num(pred.get("odds_decimal"), None) if pred.get("odds_decimal") else None
        units = units_result(grade, odds, no_odds)

        row = {
            "game_id": gid,
            "home_team_name": home,
            "away_team_name": away,
            "market": pred.get("market"),
            "pick": pred.get("best_pick"),
            "raw_confidence": pred.get("raw_confidence"),
            "calibrated_confidence": pred.get("calibrated_confidence"),
            "odds_decimal": pred.get("odds_decimal"),
            "odds_american": pred.get("odds_american"),
            "edge_flag": pred.get("edge_flag"),
            "model_edge": pred.get("model_edge"),
            "no_odds": no_odds,
            "home_score": hs,
            "away_score": as_,
            "total_runs": hs + as_,
            "run_diff": hs - as_,
            "grade": grade,
            "units_result": units,
            "roi_percent": round(units * 100, 2),
            "graded_at": now,
        }
        supabase.table("mlb_pick_grades").upsert(row, on_conflict="game_id,market,pick").execute()
        print(f"{home} vs {away} | {pred.get('best_pick')} | {hs}-{as_} | {grade} | Units {units:+.2f}")
        saved += 1

    # === Safe Zone picks ===
    safe_zones = supabase.table("mlb_safe_zone").select("*").execute().data

    for sz in safe_zones:
        gid = sz.get("game_id")
        game = finished.get(gid)
        if not game:
            continue

        hs = int(_num(game.get("home_score")))
        as_ = int(_num(game.get("away_score")))
        home = game["home_team_name"]
        away = game["away_team_name"]

        for market_label, pick_val, odds_val in [
            ("safe_balanced", sz.get("balanced_pick"), sz.get("balanced_odds_decimal")),
            ("safe_banker",   sz.get("banker_pick"),   sz.get("banker_odds_decimal")),
        ]:
            if not pick_val:
                continue

            grade = grade_mlb_safe_zone_pick(pick_val, home, away, hs, as_)
            sz_odds = _num(odds_val, None) if odds_val else None
            no_odds = sz_odds is None or sz_odds <= 1.0
            units = units_result(grade, sz_odds, no_odds)

            row = {
                "game_id": gid,
                "home_team_name": home,
                "away_team_name": away,
                "market": market_label,
                "pick": pick_val,
                "raw_confidence": None,
                "calibrated_confidence": None,
                "odds_decimal": sz_odds if not no_odds else None,
                "odds_american": None,
                "edge_flag": "no-odds" if no_odds else "REAL",
                "model_edge": None,
                "no_odds": no_odds,
                "home_score": hs,
                "away_score": as_,
                "total_runs": hs + as_,
                "run_diff": hs - as_,
                "grade": grade,
                "units_result": units,
                "roi_percent": round(units * 100, 2),
                "graded_at": now,
            }
            supabase.table("mlb_pick_grades").upsert(row, on_conflict="game_id,market,pick").execute()
            print(f"{home} vs {away} | [{market_label}] {pick_val} | {hs}-{as_} | {grade}")
            saved += 1

    print(f"\n✅ MLB picks graded: {saved}")


if __name__ == "__main__":
    main()
