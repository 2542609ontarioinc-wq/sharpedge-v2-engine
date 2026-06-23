"""
Grade all published soccer picks and summarise win-rate + ROI per market.

Step 1: call grade_soccer_picks.main() to upsert per-pick grades into
        soccer_pick_grades_v2 (WIN / LOSS / VOID rows with units_result).
Step 2: aggregate those grades into soccer_pick_results (one row per
        market bucket: overall, goals, btts, winner).

Run daily after the engine so the calibration self-improvement loop has
fresh material.  The Track Record page in /web reads from both tables.
"""

from datetime import datetime, timezone

from supabase import create_client

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from src.grading.grade_soccer_picks import main as _grade_picks

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MARKET_BUCKETS = ["overall", "goals", "btts", "winner", "safe_balanced", "safe_banker"]
# safe_zone markets are tracked separately — don't roll them into the sharp-picks "overall"
_SAFE_ZONE_MARKETS = {"safe_balanced", "safe_banker"}


def _compute_summary(rows: list[dict]) -> list[dict]:
    buckets: dict[str, list[dict]] = {k: [] for k in MARKET_BUCKETS}

    for r in rows:
        grade = r.get("grade")
        if grade not in ("WIN", "LOSS", "VOID"):
            continue
        mkt = (r.get("market") or "").lower()
        if mkt not in _SAFE_ZONE_MARKETS:
            buckets["overall"].append(r)
        if mkt in buckets:
            buckets[mkt].append(r)

    now = datetime.now(timezone.utc).isoformat()
    out = []
    for market, picks in buckets.items():
        graded = [p for p in picks if p.get("grade") in ("WIN", "LOSS")]
        wins = sum(1 for p in graded if p["grade"] == "WIN")
        losses = len(graded) - wins
        voids = sum(1 for p in picks if p.get("grade") == "VOID")
        total_units = sum(float(p.get("units_result") or 0) for p in graded)
        win_rate = round(wins / len(graded) * 100, 1) if graded else None
        # Safe zone picks have no priced odds (flat-stake categorical), so
        # units_result=0/WIN and units_result=-1/LOSS produces meaningless ROI.
        # Null out ROI and units for these markets; win rate is still valid.
        if market in _SAFE_ZONE_MARKETS:
            roi = None
            stored_units = None
        else:
            roi = round(total_units / len(graded) * 100, 2) if graded else None
            stored_units = round(total_units, 2)

        out.append(
            {
                "market": market,
                "total_picks": len(graded),
                "wins": wins,
                "losses": losses,
                "voids": voids,
                "win_rate": win_rate,
                "total_units": stored_units,
                "roi_percent": roi,
                "updated_at": now,
            }
        )

        label = f"{wins}W / {losses}L / {voids}void"
        wr = f"{win_rate}%" if win_rate is not None else "n/a"
        roi_str = f"{roi:+.1f}%" if roi is not None else "n/a"
        print(f"  {market:<8} {label:<24} WR {wr:<8} ROI {roi_str}")

    return out


def main() -> None:
    print("=== Step 1: grade individual picks ===")
    _grade_picks()

    print("\n=== Step 2: compute per-market aggregates ===")
    rows = (
        supabase.table("soccer_pick_grades_v2")
        .select("market, grade, units_result")
        .execute()
        .data
    )

    summary = _compute_summary(rows)

    supabase.table("soccer_pick_results").upsert(
        summary, on_conflict="market"
    ).execute()

    print(f"\n✅ soccer_pick_results updated: {len(summary)} market buckets")


if __name__ == "__main__":
    main()
