from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
TORONTO = ZoneInfo("America/Toronto")


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


def load_weights():
    rows = supabase.table("soccer_adaptive_weights_v1").select("*").execute().data
    return {(r["segment_type"], r["segment_value"]): r for r in rows}


def usable_weight(row):
    if not row:
        return 1.0, "No adaptive data."
    if row.get("confidence_level") == "TRACK_ONLY":
        return 1.0, "Track only sample; not applied."
    return num(row.get("adaptive_weight"), 1.0), row.get("engine_note")


def publish_status(score, current_status):
    if current_status == "REJECT":
        return "REJECT"
    if score >= 90:
        return "PUBLISH_ELITE"
    if score >= 80:
        return "PUBLISH_SAFE"
    if score >= 60:
        return "WATCHLIST"
    return "REJECT"


def main():
    weights = load_weights()
    rows = supabase.table("soccer_elite_score").select("*").execute().data

    today = datetime.now(TORONTO).date().isoformat()
    saved = 0

    for r in rows:
        notes = []
        multipliers = []

        segments = [
            ("market", r.get("market")),
            ("publish_status", r.get("publish_status")),
            ("elite_tier", r.get("elite_tier")),
            ("confidence_bucket", bucket(r.get("confidence"), 5)),
            ("elite_score_bucket", bucket(r.get("elite_score"), 5)),
            ("safety_score_bucket", bucket(r.get("safety_score_v3"), 5)),
        ]

        for stype, sval in segments:
            wrow = weights.get((stype, str(sval or "unknown")))
            weight, note = usable_weight(wrow)
            multipliers.append(weight)
            notes.append({
                "segment_type": stype,
                "segment_value": str(sval or "unknown"),
                "weight": weight,
                "note": note,
            })

        combined_weight = 1.0
        for m in multipliers:
            combined_weight *= m

        combined_weight = max(0.85, min(1.15, combined_weight))

        original_conf = num(r.get("confidence"), 0)
        original_elite = num(r.get("elite_score"), 0)

        adjusted_conf = round(max(0, min(100, original_conf * combined_weight)), 2)
        adjusted_elite = round(max(0, min(100, original_elite * combined_weight)), 2)

        adaptive_status = publish_status(adjusted_elite, r.get("publish_status"))

        out = {
            "game_id": r["game_id"],
            "home_team_name": r.get("home_team_name"),
            "away_team_name": r.get("away_team_name"),
            "market": r.get("market"),
            "pick": r.get("pick"),
            "original_confidence": original_conf,
            "adjusted_confidence": adjusted_conf,
            "original_elite_score": original_elite,
            "adjusted_elite_score": adjusted_elite,
            "adjustment_total": round((combined_weight - 1) * 100, 2),
            "adjustment_notes": notes,
            "publish_status": r.get("publish_status"),
            "adaptive_publish_status": adaptive_status,
            "run_date": today,
            "updated_at": datetime.now(TORONTO).isoformat(),
        }

        supabase.table("soccer_adaptive_prediction_adjustments_v1").upsert(
            out,
            on_conflict="game_id,market,pick,run_date",
        ).execute()

        saved += 1

    print(f"✅ Adaptive prediction adjustments upserted: {saved}")


if __name__ == "__main__":
    main()
