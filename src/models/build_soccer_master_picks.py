from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
TORONTO = ZoneInfo("America/Toronto")


def one(table, game_id, market, pick):
    rows = (
        supabase.table(table)
        .select("*")
        .eq("game_id", game_id)
        .eq("market", market)
        .eq("pick", pick)
        .limit(1)
        .execute()
        .data
    )
    return rows[0] if rows else {}


def main():
    rows = supabase.table("soccer_elite_score").select("*").execute().data
    today = datetime.now(TORONTO).date().isoformat()
    saved = 0

    for r in rows:
        game_id = r["game_id"]
        market = r.get("market")
        pick = r.get("pick")

        adaptive = one("soccer_adaptive_prediction_adjustments_v1", game_id, market, pick)
        clv = one("soccer_closing_line_value", game_id, market, pick)
        grade = one("soccer_pick_grades_v2", game_id, market, pick)

        out = {
            "game_id": game_id,
            "sport": "soccer",
            "home_team_name": r.get("home_team_name"),
            "away_team_name": r.get("away_team_name"),
            "market": market,
            "pick": pick,

            "confidence": r.get("confidence"),
            "elite_score": r.get("elite_score"),
            "adjusted_confidence": adaptive.get("adjusted_confidence"),
            "adjusted_elite_score": adaptive.get("adjusted_elite_score"),
            "safety_score": r.get("safety_score_v3"),

            "publish_status": r.get("publish_status"),
            "adaptive_publish_status": adaptive.get("adaptive_publish_status") or r.get("publish_status"),
            "elite_tier": r.get("elite_tier"),

            "odds_decimal": r.get("odds_decimal"),
            "odds_american": None,
            "bookmaker": r.get("bookmaker"),
            "closing_odds": clv.get("closing_odds"),
            "clv_percent": clv.get("clv_percent"),
            "beat_closing_line": clv.get("beat_closing_line"),

            "grade": grade.get("grade"),
            "units_result": grade.get("units_result"),
            "roi_percent": grade.get("roi_percent"),

            "failed_gates": r.get("failed_gates"),
            "passed_gates": r.get("passed_gates"),
            "score_breakdown": r.get("score_breakdown"),
            "adjustment_notes": adaptive.get("adjustment_notes"),

            "home_score": grade.get("home_score"),
            "away_score": grade.get("away_score"),
            "total_goals": grade.get("total_goals"),
            "btts": grade.get("btts"),
            "winner": grade.get("winner"),

            "notification_sent": False,
            "dashboard_visible": True,
            "run_date": today,
            "updated_at": datetime.now(TORONTO).isoformat(),
        }

        supabase.table("soccer_master_picks").upsert(
            out,
            on_conflict="game_id,market,pick,run_date",
        ).execute()

        saved += 1

    print(f"✅ Soccer master picks upserted: {saved}")


if __name__ == "__main__":
    main()
