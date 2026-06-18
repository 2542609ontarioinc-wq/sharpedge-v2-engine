from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.sync_team_form import get_last_matches_for_team


def extract_api_team_id(raw_json, side):
    return raw_json["teams"][side]["id"]


def calculate_form(team_api_id, team_name):
    data = get_last_matches_for_team(team_api_id)
    fixtures = data.get("response", [])

    wins = draws = losses = 0
    goals_for = goals_against = 0

    for item in fixtures:
        teams = item.get("teams", {})
        goals = item.get("goals", {})

        home = teams.get("home", {})
        away = teams.get("away", {})

        is_home = home.get("id") == team_api_id

        gf = goals.get("home") if is_home else goals.get("away")
        ga = goals.get("away") if is_home else goals.get("home")

        gf = gf or 0
        ga = ga or 0

        goals_for += gf
        goals_against += ga

        if gf > ga:
            wins += 1
        elif gf == ga:
            draws += 1
        else:
            losses += 1

    matches = len(fixtures)
    points = wins * 3 + draws
    form_score = round((points / (matches * 3)) * 100, 2) if matches else 50

    return {
        "matches_checked": matches,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals_for": goals_for,
        "goals_against": goals_against,
        "form_score": form_score,
    }


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    games = (
        supabase.table("games")
        .select("id,league_key,home_team_name,away_team_name,raw_json")
        .eq("sport_key", "soccer")
        .in_("league_key", ["1", "479"])
        .execute()
    ).data

    saved = 0

    for game in games:
        raw = game["raw_json"]

        for side in ["home", "away"]:
            team_api_id = extract_api_team_id(raw, side)
            team_name = raw["teams"][side]["name"]

            form = calculate_form(team_api_id, team_name)

            row = {
                "game_id": game["id"],
                "team_name": team_name,
                "league_key": game["league_key"],
                **form,
            }

            supabase.table("soccer_form_features").insert(row).execute()
            saved += 1

    print(f"✅ Real team form rows created: {saved}")


if __name__ == "__main__":
    main()
    