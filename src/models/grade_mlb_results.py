"""
Grade all published MLB picks and summarise win-rate + ROI per market.

Step 1: grade_mlb_picks → upsert per-pick grades into mlb_pick_grades.
Step 2: aggregate mlb_pick_grades → mlb_pick_results (game-level buckets).
Step 3: grade_mlb_prop_picks → upsert per-prop grades into mlb_prop_grades.
Step 4: print prop summary by market bucket (strikeouts / outs / etc.).

Run daily after the engine so the track record stays fresh.
"""
from datetime import datetime, timezone

from supabase import create_client

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from src.grading.grade_mlb_picks import main as _grade_picks
from src.grading.grade_mlb_prop_picks import main as _grade_prop_picks

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MARKET_BUCKETS = ["overall", "moneyline", "totals", "run_line", "safe_balanced", "safe_banker"]
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
        roi = round(total_units / len(graded) * 100, 2) if graded else None

        out.append(
            {
                "market": market,
                "total_picks": len(graded),
                "wins": wins,
                "losses": losses,
                "voids": voids,
                "win_rate": win_rate,
                "total_units": round(total_units, 2),
                "roi_percent": roi,
                "updated_at": now,
            }
        )

        label = f"{wins}W / {losses}L / {voids}void"
        wr = f"{win_rate}%" if win_rate is not None else "n/a"
        roi_str = f"{roi:+.1f}%" if roi is not None else "n/a"
        print(f"  {market:<14} {label:<24} WR {wr:<8} ROI {roi_str}")

    return out


def _print_prop_summary(rows: list[dict]) -> None:
    """Print per-market win-rate summary for prop grades (no DB write needed yet)."""
    from collections import defaultdict
    by_market: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        mkt = r.get("prop_market") or "unknown"
        if r.get("grade") in ("WIN", "LOSS", "VOID"):
            by_market[mkt].append(r)

    print(f"\n  {'market':<16} {'W/L/V':<16} {'WR':>6}  {'ROI':>8}")
    for mkt in sorted(by_market):
        picks = by_market[mkt]
        graded = [p for p in picks if p.get("grade") in ("WIN", "LOSS")]
        wins = sum(1 for p in graded if p["grade"] == "WIN")
        losses = len(graded) - wins
        voids = sum(1 for p in picks if p.get("grade") == "VOID")
        units = sum(float(p.get("units_result") or 0) for p in graded)
        wr = f"{wins / len(graded) * 100:.1f}%" if graded else "n/a"
        roi = f"{units / len(graded) * 100:+.1f}%" if graded else "n/a"
        print(f"  {mkt:<16} {wins}W/{losses}L/{voids}V{'':5} {wr:>6}  {roi:>8}")


def main() -> None:
    print("=== Step 1: grade individual MLB game picks ===")
    _grade_picks()

    print("\n=== Step 2: compute per-market aggregates (game picks) ===")
    rows = (
        supabase.table("mlb_pick_grades")
        .select("market, grade, units_result")
        .execute()
        .data
    )

    summary = _compute_summary(rows)
    supabase.table("mlb_pick_results").upsert(summary, on_conflict="market").execute()
    print(f"\n✅ mlb_pick_results updated: {len(summary)} market buckets")

    print("\n=== Step 3: grade MLB player prop picks ===")
    _grade_prop_picks()

    print("\n=== Step 4: prop summary by market ===")
    prop_rows = (
        supabase.table("mlb_prop_grades")
        .select("prop_market, grade, units_result")
        .execute()
        .data
    )
    _print_prop_summary(prop_rows)


if __name__ == "__main__":
    main()
