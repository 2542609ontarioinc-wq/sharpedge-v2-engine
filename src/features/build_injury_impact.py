from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    games = (
        supabase.table("games")
        .select("id, home_team_name, away_team_name, league_key, raw_json")
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

        injuries_data = enriched.get("injuries") or {}
        injuries = injuries_data.get("response", []) if isinstance(injuries_data, dict) else []

        home_injuries = 0
        away_injuries = 0

        for item in injuries:
            team = item.get("team", {})
            team_name = team.get("name")

            if team_name == game["home_team_name"]:
                home_injuries += 1

            if team_name == game["away_team_name"]:
                away_injuries += 1

        total = home_injuries + away_injuries
        available = total > 0

        # Positive score means away has more injuries, home benefits.
        # Negative score means home has more injuries, away benefits.
        impact_score = away_injuries - home_injuries

        row = {
            "game_id": game["id"],
            "home_team_name": game["home_team_name"],
            "away_team_name": game["away_team_name"],
            "total_injuries": total,
            "home_injuries": home_injuries,
            "away_injuries": away_injuries,
            "injury_available": available,
            "injury_impact_score": impact_score,
        }

        supabase.table("soccer_injury_impact").insert(row).execute()
        saved += 1

    print(f"✅ Injury impact rows created: {saved}")


if __name__ == "__main__":
    main()
    