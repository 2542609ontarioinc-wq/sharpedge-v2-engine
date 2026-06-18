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


def clamp(value, low=0, high=100):
    return max(low, min(high, round(value, 2)))


def edge_score(edge):
    if edge is None:
        return 0
    if edge >= 15:
        return 100
    if edge >= 10:
        return 85
    if edge >= 6:
        return 70
    if edge >= 3:
        return 45
    if edge > 0:
        return 25
    return 0


def market_quality_score(odds_decimal, bookmaker):
    if odds_decimal and bookmaker:
        return 100
    if odds_decimal:
        return 65
    return 0


def has_failed_gate(row, gate_name):
    failed = row.get("failed_gates") or []
    return any(g.get("gate") == gate_name for g in failed)


def tier(score, safety_status, row):
    lineup_failed = has_failed_gate(row, "Lineups")
    ev_failed = has_failed_gate(row, "Expected Value")
    edge_failed = has_failed_gate(row, "Model Edge")
    odds_failed = has_failed_gate(row, "Odds Quality")

    hard_failed = lineup_failed or ev_failed or edge_failed or odds_failed

    if hard_failed:
        if score >= 60:
            return "Watchlist"
        return "Reject"

    if safety_status == "ELITE" and score >= 88:
        return "Elite"
    if safety_status in ["ELITE", "SAFE"] and score >= 78:
        return "Safe"
    if score >= 60:
        return "Watchlist"
    return "Reject"


def publish_status_from_tier(t):
    if t == "Elite":
        return "PUBLISH_ELITE"
    if t == "Safe":
        return "PUBLISH_SAFE"
    if t == "Watchlist":
        return "WATCHLIST"
    return "REJECT"


def recommendation(t):
    if t == "Elite":
        return "Publish as top premium pick."
    if t == "Safe":
        return "Publish as official safe pick."
    if t == "Watchlist":
        return "Do not publish as official pick yet. Monitor for lineup/market confirmation."
    return "Do not publish."


def main():
    rows = supabase.table("soccer_safety_engine_v3").select("*").execute().data

    today = datetime.now(TORONTO).date().isoformat()
    saved = 0

    for row in rows:
        safety = num(row.get("safety_score_v3"))
        conf = num(row.get("confidence"))
        edge = row.get("model_edge")
        edge_n = num(edge, None)
        odds = num(row.get("odds_decimal"), None)
        bookmaker = row.get("bookmaker")
        safety_status = row.get("safety_status_v3")

        conf_component = clamp(conf)
        edge_component = edge_score(edge_n)
        market_component = market_quality_score(odds, bookmaker)
        safety_component = safety

        elite = clamp(
            (0.35 * safety_component)
            + (0.25 * edge_component)
            + (0.25 * conf_component)
            + (0.15 * market_component)
        )

        t = tier(elite, safety_status, row)
        publish = publish_status_from_tier(t)

        breakdown = {
            "safety_component": safety_component,
            "edge_component": edge_component,
            "confidence_component": conf_component,
            "market_component": market_component,
            "weights": {
                "safety": 0.35,
                "edge": 0.25,
                "confidence": 0.25,
                "market": 0.15,
            },
        }

        out = {
            "game_id": row["game_id"],
            "home_team_name": row.get("home_team_name"),
            "away_team_name": row.get("away_team_name"),
            "pick": row.get("pick"),
            "market": row.get("market"),
            "confidence": row.get("confidence"),
            "model_edge": row.get("model_edge"),
            "odds_decimal": row.get("odds_decimal"),
            "bookmaker": row.get("bookmaker"),
            "safety_score_v3": safety,
            "elite_score": elite,
            "elite_tier": t,
            "publish_status": publish,
            "publish_recommendation": recommendation(t),
            "score_breakdown": breakdown,
            "failed_gates": row.get("failed_gates"),
            "passed_gates": row.get("passed_gates"),
            "run_date": today,
        }

        supabase.table("soccer_elite_score").upsert(
            out,
            on_conflict="game_id,market,pick,run_date",
        ).execute()

        saved += 1

    print(f"✅ Soccer elite scores upserted: {saved}")


if __name__ == "__main__":
    main()
