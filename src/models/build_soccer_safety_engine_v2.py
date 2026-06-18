from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
TORONTO = ZoneInfo("America/Toronto")


def num(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def gate_status(passed):
    return "PASS" if passed else "FAIL"


def build_gate_notes(row):
    notes = []
    score = 100

    confidence = num(row.get("confidence"), 0)
    model_edge = num(row.get("model_edge"))
    odds_decimal = num(row.get("odds_decimal"))
    implied = num(row.get("market_implied_probability"))
    bookmaker = row.get("bookmaker")
    market = row.get("market")

    if confidence >= 75:
        notes.append("PASS: Confidence is strong.")
    elif confidence >= 65:
        notes.append("WATCH: Confidence is playable but not elite.")
        score -= 12
    else:
        notes.append("FAIL: Confidence is below safe-pick threshold.")
        score -= 28

    if odds_decimal:
        notes.append("PASS: Sportsbook odds are matched.")
    else:
        notes.append("FAIL: No sportsbook odds matched.")
        score -= 25

    if bookmaker:
        notes.append(f"PASS: Bookmaker confirmed: {bookmaker}.")
    else:
        notes.append("FAIL: No confirmed bookmaker source.")
        score -= 15

    if model_edge is None:
        notes.append("FAIL: Model edge has not been calculated.")
        score -= 25
    elif model_edge >= 8:
        notes.append("PASS: Strong positive model edge.")
    elif model_edge >= 5:
        notes.append("WATCH: Edge is positive but moderate.")
        score -= 8
    elif model_edge > 0:
        notes.append("FAIL: Edge is too small for safe-pick status.")
        score -= 22
    else:
        notes.append("FAIL: No positive value edge.")
        score -= 32

    if implied is not None:
        notes.append("PASS: Market implied probability available.")
    else:
        notes.append("WATCH: Market implied probability missing.")
        score -= 8

    if market in ["goals", "btts", "winner"]:
        notes.append("PASS: Supported core soccer market.")
    else:
        notes.append("WATCH: Market is supported but needs tighter validation.")
        score -= 5

    score = max(0, min(100, round(score, 2)))

    if score >= 85:
        status = "ELITE_SAFE"
        label = "Elite Safe"
        recommendation = "Official safe pick. Strong enough for premium card."
    elif score >= 72:
        status = "SAFE"
        label = "Safe"
        recommendation = "Playable safe pick, but not top-tier elite."
    elif score >= 55:
        status = "WATCHLIST"
        label = "Watchlist"
        recommendation = "Model lean only. Do not publish as official safe pick yet."
    else:
        status = "REJECT"
        label = "Rejected"
        recommendation = "Do not publish. Too many failed safety gates."

    return score, status, label, recommendation, notes


def main():
    rows = (
        supabase.table("final_soccer_predictions")
        .select("*")
        .execute()
        .data
    )

    saved = 0
    today = datetime.now(TORONTO).date().isoformat()

    for row in rows:
        score, status, label, recommendation, notes = build_gate_notes(row)

        out = {
            "game_id": row["game_id"],
            "home_team_name": row.get("home_team_name"),
            "away_team_name": row.get("away_team_name"),
            "pick": row.get("best_pick"),
            "market": row.get("market"),
            "confidence": row.get("confidence"),
            "bookmaker": row.get("bookmaker"),
            "odds_decimal": row.get("odds_decimal"),
            "odds_american": row.get("odds_american"),
            "market_implied_probability": row.get("market_implied_probability"),
            "model_edge": row.get("model_edge"),
            "safety_score_v2": score,
            "safety_status_v2": status,
            "safety_label_v2": label,
            "recommendation_v2": recommendation,
            "gate_notes": notes,
            "run_date": today,
        }

        supabase.table("soccer_safety_engine_v2").upsert(
            out,
            on_conflict="game_id,market,pick,run_date",
        ).execute()

        saved += 1

    print(f"✅ Soccer Safety Engine V2 rows upserted: {saved}")


if __name__ == "__main__":
    main()
    