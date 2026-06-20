"""
Hourly incremental grading for MLB picks.

Checks whether any games that have picks in mlb_final_predictions or
mlb_safe_zone have just become Final but are not yet in mlb_pick_grades.
If new finals are found, runs the full grading + detail + CLV + subscriber
rebuild chain.  If nothing is new, exits immediately with no work done.

All grading guards (final-only, postponed, 0-0 placeholder) live in
grade_mlb_picks.py and are imported unchanged — this module only decides
*whether* to call them.
"""
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.grading.grade_mlb_picks import FINISHED_STATUSES, POSTPONED_STATUSES, _is_finished
from src.grading.grade_mlb_picks import main as _grade_picks
from src.grading.grade_mlb_prop_picks import main as _grade_prop_picks
from src.grading.build_mlb_pick_detail import main as _build_pick_detail
from src.grading.build_mlb_prop_detail import main as _build_prop_detail
from src.models.build_mlb_clv import main as _build_clv
from src.analytics.build_mlb_subscriber_analytics import main as _build_subscriber

SPORT_KEY = "baseball_mlb"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _find_new_finals() -> set[str]:
    """
    Return game_ids that are now finished AND have picks but no grade yet.
    Uses _is_finished() from grade_mlb_picks exactly — same guards apply.
    """
    # All game_ids with picks.
    pred_rows = supabase.table("mlb_final_predictions").select("game_id").execute().data or []
    sz_rows = supabase.table("mlb_safe_zone").select("game_id").execute().data or []
    pick_ids = {r["game_id"] for r in pred_rows + sz_rows if r.get("game_id")}

    if not pick_ids:
        return set()

    # Finished game_ids (uses the same _is_finished() guard from grade_mlb_picks.py).
    games = (
        supabase.table("games")
        .select("id,status,period")
        .eq("sport_key", SPORT_KEY)
        .in_("id", list(pick_ids))
        .execute()
        .data
    ) or []
    finished_ids = {g["id"] for g in games if _is_finished(g)}

    if not finished_ids:
        return set()

    # Already-graded game_ids.
    graded_rows = (
        supabase.table("mlb_pick_grades")
        .select("game_id")
        .in_("game_id", list(finished_ids))
        .execute()
        .data
    ) or []
    graded_ids = {r["game_id"] for r in graded_rows}

    # New finals = finished games that have no grade record at all.
    # (The grading upsert is idempotent, so if a grade exists and is stale
    # it will be refreshed anyway — but we only trigger the full rebuild
    # when there is genuinely new work to do.)
    return finished_ids - graded_ids


def main() -> None:
    new_finals = _find_new_finals()

    if not new_finals:
        print("  [incremental-grade] No new final games — nothing to do.")
        return

    print(f"  [incremental-grade] {len(new_finals)} newly finished game(s) found — grading now.")
    for gid in sorted(new_finals):
        print(f"    {gid}")

    print("\n=== [Incremental] Grade MLB game picks ===")
    _grade_picks()

    print("\n=== [Incremental] Grade MLB prop picks ===")
    _grade_prop_picks()

    print("\n=== [Incremental] Build pick detail ===")
    _build_pick_detail()

    print("\n=== [Incremental] Build prop detail ===")
    _build_prop_detail()

    print("\n=== [Incremental] Build CLV ===")
    _build_clv()

    print("\n=== [Incremental] Build subscriber analytics ===")
    _build_subscriber()

    print(f"\n✅ Incremental grading complete for {len(new_finals)} new final(s).")


if __name__ == "__main__":
    main()
