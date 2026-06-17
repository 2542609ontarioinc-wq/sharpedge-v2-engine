from collections import defaultdict
from datetime import datetime, timezone

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def num(value, default=0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def bucket(value, size=5):
    v = num(value, None)
    if v is None:
        return "unknown"
    low = int(v // size) * size
    high = low + size - 1
    return f"{low}-{high}"


def add_segment(segments, segment_type, segment_value, row):
    key = (segment_type, str(segment_value or "unknown"))
    segments[key].append(row)


def summarize(rows):
    total = len(rows)
    wins = sum(1 for r in rows if r.get("grade") == "WIN")
    losses = sum(1 for r in rows if r.get("grade") == "LOSS")
    pushes = sum(1 for r in rows if r.get("grade") == "PUSH")
    voids = sum(1 for r in rows if r.get("grade") == "VOID")

    graded = wins + losses
    win_rate = round((wins / graded) * 100, 2) if graded else 0

    total_units = round(sum(num(r.get("units_result"), 0) for r in rows), 2)
    roi = round((total_units / total) * 100, 2) if total else 0

    clvs = [num(r.get("clv_percent"), None) for r in rows if r.get("clv_percent") is not None]
    avg_clv = round(sum(clvs) / len(clvs), 2) if clvs else 0

    if total < 10:
        adj = 0
        note = "Sample too small. Track only."
    elif roi >= 15 and win_rate >= 55:
        adj = 10
        note = "Strong profitable segment. Increase model trust."
    elif roi >= 5:
        adj = 5
        note = "Positive segment. Slightly increase weight."
    elif roi <= -15:
        adj = -10
        note = "Poor segment. Reduce model trust."
    elif roi < 0:
        adj = -5
        note = "Negative segment. Slightly reduce weight."
    else:
        adj = 0
        note = "Neutral segment."

    return total, wins, losses, pushes, voids, win_rate, total_units, roi, avg_clv, adj, note


def main():
    rows = (
        supabase.table("soccer_pick_grades_v2")
        .select("*")
        .execute()
        .data
    )

    segments = defaultdict(list)

    for r in rows:
        add_segment(segments, "market", r.get("market"), r)
        add_segment(segments, "publish_status", r.get("publish_status"), r)
        add_segment(segments, "elite_tier", r.get("elite_tier"), r)
        add_segment(segments, "confidence_bucket", bucket(r.get("confidence"), 5), r)
        add_segment(segments, "elite_score_bucket", bucket(r.get("elite_score"), 5), r)
        add_segment(segments, "safety_score_bucket", bucket(r.get("safety_score"), 5), r)
        add_segment(segments, "clv_bucket", bucket(r.get("clv_percent"), 2), r)

    saved = 0

    for (segment_type, segment_value), segment_rows in segments.items():
        total, wins, losses, pushes, voids, win_rate, total_units, roi, avg_clv, adj, note = summarize(segment_rows)

        out = {
            "segment_type": segment_type,
            "segment_value": segment_value,
            "total_picks": total,
            "wins": wins,
            "losses": losses,
            "pushes": pushes,
            "voids": voids,
            "win_rate": win_rate,
            "total_units": total_units,
            "roi_percent": roi,
            "avg_clv_percent": avg_clv,
            "recommended_weight_adjustment": adj,
            "engine_note": note,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        supabase.table("soccer_analytics_feedback_v1").upsert(
            out,
            on_conflict="segment_type,segment_value",
        ).execute()

        saved += 1

    print(f"✅ Soccer analytics feedback rows upserted: {saved}")


if __name__ == "__main__":
    main()
