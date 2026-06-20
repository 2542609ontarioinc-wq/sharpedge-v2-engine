"""
Compute and store subscriber track-record aggregates.

Sources:
  mlb_pick_detail  — graded game picks (moneyline / totals / run_line / safe_zone)
  mlb_prop_detail  — graded player prop picks

Reads subscriber_qualified = true rows, aggregates per segment ('all' and 'bet_of_day'),
and writes one row per segment to mlb_subscriber_results.

Honesty ordering:
  PRIMARY:   avg_clv, clv_beat_rate — edge over closing line (most rigorous signal)
  SECONDARY: win_rate, roi_percent  — subject to favourites bias; report but don't lead with it
"""
from datetime import datetime, timezone

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _agg(rows):
    """
    Compute aggregate stats from a list of detail rows.
    Returns a dict ready to upsert into mlb_subscriber_results.
    """
    graded = [r for r in rows if r.get("grade") in ("WIN", "LOSS")]
    if not graded:
        return {
            "pick_count": 0, "win_count": 0, "loss_count": 0,
            "win_rate": None, "units_profit": None, "roi_percent": None,
            "avg_edge": None, "avg_win_prob": None,
            "avg_clv": None, "clv_beat_rate": None,
        }

    wins   = sum(1 for r in graded if r.get("grade") == "WIN")
    losses = sum(1 for r in graded if r.get("grade") == "LOSS")
    n      = wins + losses

    # ROI: only over rows with real odds (units_result != 0 on WIN, or the row was a LOSS)
    # Prop rows have no `no_odds` flag — use best_odds_decimal proxy.
    # Pick rows have an explicit `no_odds` boolean.
    roi_rows = []
    for r in graded:
        no_odds = r.get("no_odds")  # pick_detail field; None for prop rows
        if no_odds is None:
            # prop row: real odds when best_odds_decimal > 1.0
            odds = _f(r.get("best_odds_decimal"))
            no_odds = not (odds is not None and odds > 1.0)
        if not no_odds:
            roi_rows.append(r)

    units = sum(_f(r.get("units_result")) or 0.0 for r in roi_rows)
    roi   = round(units / len(roi_rows) * 100, 2) if roi_rows else None

    # Average model edge — only rows with an edge signal (sharp picks + props)
    edges = [_f(r.get("model_edge")) for r in graded if _f(r.get("model_edge")) is not None]
    avg_edge = round(sum(edges) / len(edges), 2) if edges else None

    # Average win-probability at pick time
    # pick_detail: calibrated_conf is win-prob for the picked side (already correct)
    # prop_detail: calibrated_prob is Over-prob; flip for Under picks
    probs = []
    for r in graded:
        if "calibrated_conf" in r and r.get("calibrated_conf") is not None:
            # pick_detail row
            p = _f(r["calibrated_conf"])
            if p is not None:
                probs.append(p)
        elif r.get("calibrated_prob") is not None:
            # prop_detail row: flip if Under pick
            p = _f(r["calibrated_prob"])
            if p is not None:
                side = (r.get("pick_side") or "").strip().lower()
                probs.append(100.0 - p if side == "under" else p)

    avg_prob = round(sum(probs) / len(probs), 2) if probs else None

    # CLV — only available on pick_detail rows (not props)
    clv_vals = [_f(r.get("clv")) for r in graded if _f(r.get("clv")) is not None]
    avg_clv  = round(sum(clv_vals) / len(clv_vals), 3) if clv_vals else None

    beat_rows = [r for r in graded if r.get("beat_close") is not None]
    clv_beat_rate = (
        round(sum(1 for r in beat_rows if r.get("beat_close")) / len(beat_rows), 4)
        if beat_rows else None
    )

    return {
        "pick_count":   n,
        "win_count":    wins,
        "loss_count":   losses,
        "win_rate":     round(wins / n, 4) if n else None,
        "units_profit": round(units, 3) if roi_rows else None,
        "roi_percent":  roi,
        "avg_edge":     avg_edge,
        "avg_win_prob": avg_prob,
        "avg_clv":      avg_clv,
        "clv_beat_rate": clv_beat_rate,
    }


def main():
    # Load subscriber-qualified graded rows from both detail tables
    pick_rows = (
        supabase.table("mlb_pick_detail")
        .select(
            "grade, units_result, no_odds, model_edge, calibrated_conf, "
            "odds_decimal, clv, beat_close, bet_of_day"
        )
        .eq("subscriber_qualified", True)
        .execute()
        .data
    )

    prop_rows = (
        supabase.table("mlb_prop_detail")
        .select(
            "grade, units_result, best_odds_decimal, model_edge, "
            "calibrated_prob, pick_side, bet_of_day"
        )
        .eq("subscriber_qualified", True)
        .execute()
        .data
    )

    all_rows  = pick_rows + prop_rows
    botd_rows = [r for r in all_rows if r.get("bet_of_day")]

    now = datetime.now(timezone.utc).isoformat()

    print("\nSUBSCRIBER TRACK RECORD")
    print("=" * 60)
    print(
        "  NOTE: CLV (closing-line value) is the primary signal.\n"
        "  win_rate / ROI are secondary — subject to favourites bias.\n"
        f"  All segment:      {len(all_rows)} subscriber-qualified rows loaded\n"
        f"  Bet of the Day:   {len(botd_rows)} rows\n"
    )

    for segment, rows in [("all", all_rows), ("bet_of_day", botd_rows)]:
        stats = _agg(rows)
        row = {
            "segment": segment,
            **stats,
            "computed_at": now,
        }
        supabase.table("mlb_subscriber_results").upsert(
            row, on_conflict="segment"
        ).execute()

        n     = stats["pick_count"]
        wl    = f"{stats['win_count']}-{stats['loss_count']}" if n else "—"
        wr    = f"{stats['win_rate']:.1%}" if stats["win_rate"] is not None else "—"
        roi   = f"{stats['roi_percent']:+.1f}%" if stats["roi_percent"] is not None else "—"
        edge  = f"+{stats['avg_edge']:.1f}%" if stats["avg_edge"] is not None else "—"
        prob  = f"{stats['avg_win_prob']:.1f}%" if stats["avg_win_prob"] is not None else "—"
        clv   = f"{stats['avg_clv']:+.2f}%" if stats["avg_clv"] is not None else "(no data yet)"
        print(
            f"  [{segment:12s}] n={n:3d}  W-L={wl:7s}  WR={wr}  "
            f"ROI={roi}  AvgEdge={edge}  WinProb={prob}  CLV={clv}"
        )

    print("\n✅ Subscriber analytics updated")


if __name__ == "__main__":
    main()
