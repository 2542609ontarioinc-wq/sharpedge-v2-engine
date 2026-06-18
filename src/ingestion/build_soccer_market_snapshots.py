from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    rows = (
        supabase.table("soccer_odds")
        .select("*")
        .order("captured_at", desc=True)
        .limit(5000)
        .execute()
        .data
    )

    saved = 0

    for row in rows:
        snapshot = {
            "game_id": row.get("game_id"),
            "home_team_name": row.get("home_team_name"),
            "away_team_name": row.get("away_team_name"),
            "market": row.get("market"),
            "selection": row.get("selection"),
            "bookmaker": row.get("bookmaker"),
            "odds_decimal": row.get("odds_decimal"),
            "odds_american": row.get("odds_american"),
            "implied_probability": row.get("implied_probability"),
        }

        supabase.table("soccer_market_snapshots").insert(snapshot).execute()
        saved += 1

    print(f"✅ Market snapshots created: {saved}")


if __name__ == "__main__":
    main()
    