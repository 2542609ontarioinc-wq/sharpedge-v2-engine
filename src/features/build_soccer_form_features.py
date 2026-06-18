from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY


def calculate_placeholder_form(team_name):
    # Temporary placeholder.
    # Next version will pull last 5 real matches from API-Sports.
    return {
        "matches_checked": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
        "form_score": 50,
    }


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    priority_result = (
        supabase.table("priority_leagues")
        .select("league_id")
        .eq("sport_key", "soccer")
        .eq("enabled", True)
        .execute()
    )

    priority_ids = [row["league_id"] for row in priority_result.data]

    games_result = (
        supabase.table("games")
        .select("id, league_key, home_team_id, away_team_id, home_team_name, away_team_name")
        .eq("sport_key", "soccer")
        .in_("league_key", priority_ids)
        .limit(100)
        .execute()
    )

    games = games_result.data or []

    print(f"Priority games found: {len(games)}")

    saved = 0

    for game in games:
        for side in ["home", "away"]:
            team_id = game[f"{side}_team_id"]
            team_name = game[f"{side}_team_name"]

            form = calculate_placeholder_form(team_name)

            row = {
                "game_id": game["id"],
                "team_id": team_id,
                "team_name": team_name,
                "league_key": game["league_key"],
                **form,
            }

            supabase.table("soccer_form_features").insert(row).execute()
            saved += 1

    print(f"✅ Soccer form feature rows created: {saved}")


if __name__ == "__main__":
    main()
    