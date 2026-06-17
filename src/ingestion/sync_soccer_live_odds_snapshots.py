from datetime import datetime, timezone
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    rows = (
        supabase.table("final_soccer_predictions")
        .select("*")
        .execute()
        .data
    )

    saved = 0
    now = datetime.now(timezone.utc).isoformat()

    for r in rows:
        if not r.get("odds_decimal"):
            continue

        out = {
            "game_id": r["game_id"],
            "home_team_name": r.get("home_team_name"),
            "away_team_name": r.get("away_team_name"),
            "market": r.get("market"),
            "pick": r.get("best_pick"),
            "bookmaker": r.get("bookmaker"),
            "odds_decimal": r.get("odds_decimal"),
            "odds_american": r.get("odds_american"),
            "implied_probability": r.get("market_implied_probability"),
            "snapshot_source": "live_monitor",
            "captured_at": now,
        }

        supabase.table("soccer_live_odds_snapshots").insert(out).execute()
        saved += 1

    print(f"✅ Live odds snapshots saved: {saved}")


if __name__ == "__main__":
    main()