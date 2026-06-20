"""
Grade settled per-model picks for all MLB model versions.

Reads mlb_model_picks for every version; grades the sharp pick against finished
games.  Writes one row per (game_id, model_version) to mlb_model_grades.

Grading logic is the same as grade_mlb_picks.py (imported, not duplicated).
"""
from datetime import datetime, timezone

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.grading.grade_mlb_picks import grade_mlb_pick, units_result

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"
FINISHED_STATUSES = {"ft", "aot", "f", "final", "game finished", "finished"}
# "post" = API-Sports status for Postponed; must be caught even when period is not yet set.
POSTPONED_STATUSES = {"postponed", "cancelled", "canceled", "suspended", "post"}


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _is_finished(g):
    status = (g.get("status") or "").lower()
    period = (g.get("period") or "").lower()
    if status in POSTPONED_STATUSES or period in POSTPONED_STATUSES:
        return False
    return status in FINISHED_STATUSES or period in FINISHED_STATUSES


def main():
    games = (
        supabase.table("games")
        .select("id,game_date,home_team_name,away_team_name,home_score,away_score,status,period")
        .eq("sport_key", SPORT_KEY)
        .execute()
        .data
    )
    finished = {g["id"]: g for g in games if _is_finished(g)}

    picks = supabase.table("mlb_model_picks").select("*").execute().data

    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    skipped = 0

    for pick in picks:
        gid = pick.get("game_id")
        game = finished.get(gid)
        if not game:
            skipped += 1
            continue

        hs = int(_num(game.get("home_score")))
        as_ = int(_num(game.get("away_score")))
        if hs == 0 and as_ == 0:
            skipped += 1
            continue
        home = game["home_team_name"]
        away = game["away_team_name"]

        grade = grade_mlb_pick(
            pick.get("market"), pick.get("best_pick"), home, away, hs, as_
        )

        no_odds = (pick.get("edge_flag") or "") == "no-odds"
        odds = _num(pick.get("odds_decimal"), None) if pick.get("odds_decimal") else None
        units = units_result(grade, odds, no_odds)

        row = {
            "game_id": gid,
            "model_version": pick.get("model_version"),
            "home_team_name": home,
            "away_team_name": away,
            "market": pick.get("market"),
            "pick": pick.get("best_pick"),
            "raw_confidence": pick.get("raw_confidence"),
            "calibrated_confidence": pick.get("calibrated_confidence"),
            "odds_decimal": pick.get("odds_decimal"),
            "odds_american": pick.get("odds_american"),
            "edge_flag": pick.get("edge_flag"),
            "model_edge": pick.get("model_edge"),
            "no_odds": no_odds,
            "home_score": hs,
            "away_score": as_,
            "total_runs": hs + as_,
            "run_diff": hs - as_,
            "grade": grade,
            "units_result": units,
            "roi_percent": round(units * 100, 2),
            "game_date": game.get("game_date"),
            "graded_at": now,
        }

        supabase.table("mlb_model_grades").upsert(
            row, on_conflict="game_id,model_version"
        ).execute()
        print(
            f"[{pick.get('model_version')}] {home} vs {away} | "
            f"{pick.get('best_pick')} | {hs}-{as_} | {grade} | {units:+.2f}u"
        )
        saved += 1

    print(f"\n✅ MLB model picks graded: {saved} | pending (no result yet): {skipped}")


if __name__ == "__main__":
    main()
