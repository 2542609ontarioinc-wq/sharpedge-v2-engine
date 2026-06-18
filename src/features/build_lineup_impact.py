from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    games = (
        supabase.table("games")
        .select("id, home_team_name, away_team_name, raw_json")
        .eq("sport_key", "soccer")
.in_("league_key", ["1", "479"])
.limit(50)
        .execute()
        .data
    )

    saved = 0

    for game in games:
        raw = game.get("raw_json") or {}
        enriched = raw.get("enriched_details") or {}
        lineups = enriched.get("lineups", {}).get("response", [])

        home_count = 0
        away_count = 0

        for item in lineups:
            team = item.get("team", {})
            players = item.get("startXI", [])

            if team.get("name") == game["home_team_name"]:
                home_count = len(players)

            if team.get("name") == game["away_team_name"]:
                away_count = len(players)

        lineup_available = home_count > 0 or away_count > 0

        impact_score = 10 if lineup_available else 0

        supabase.table("soccer_lineup_impact").insert(
            {
                "game_id": game["id"],
                "home_team_name": game["home_team_name"],
                "away_team_name": game["away_team_name"],
                "home_lineup_count": home_count,
                "away_lineup_count": away_count,
                "lineup_available": lineup_available,
                "lineup_impact_score": impact_score,
            }
        ).execute()

        saved += 1

    print(f"✅ Lineup impact rows created: {saved}")


if __name__ == "__main__":
    main()
