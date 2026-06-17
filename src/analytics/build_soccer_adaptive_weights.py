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


def confidence_level(sample):
    if sample >= 100:
        return "HIGH"
    if sample >= 30:
        return "MEDIUM"
    if sample >= 10:
        return "LOW"
    return "TRACK_ONLY"


def adaptive_weight(base, adjustment, sample):
    if sample < 10:
        return base

    capped_adjustment = max(-15, min(15, num(adjustment, 0)))
    return round(base * (1 + capped_adjustment / 100), 4)


def main():
    rows = (
        supabase.table("soccer_analytics_feedback_v1")
        .select("*")
        .execute()
        .data
    )

    saved = 0

    for r in rows:
        sample = int(r.get("total_picks") or 0)
        base = 1.0
        adjustment = num(r.get("recommended_weight_adjustment"), 0)
        weight = adaptive_weight(base, adjustment, sample)

        level = confidence_level(sample)

        if level == "TRACK_ONLY":
            note = "Not enough graded picks yet. Do not apply weight."
        elif weight > 1:
            note = "Positive segment. Increase trust."
        elif weight < 1:
            note = "Negative segment. Reduce trust."
        else:
            note = "Neutral segment."

        out = {
            "segment_type": r.get("segment_type"),
            "segment_value": r.get("segment_value"),
            "base_weight": base,
            "recommended_adjustment": adjustment,
            "adaptive_weight": weight,
            "sample_size": sample,
            "roi_percent": r.get("roi_percent"),
            "win_rate": r.get("win_rate"),
            "avg_clv_percent": r.get("avg_clv_percent"),
            "confidence_level": level,
            "engine_note": note,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        supabase.table("soccer_adaptive_weights_v1").upsert(
            out,
            on_conflict="segment_type,segment_value",
        ).execute()

        saved += 1

    print(f"✅ Soccer adaptive weights upserted: {saved}")


if __name__ == "__main__":
    main()
