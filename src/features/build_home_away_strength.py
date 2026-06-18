from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_latest_form(game_id, team_name):
    rows = (
        supabase.table("soccer_form_features")
        .select("*")
        .eq("game_id", game_id)
        .eq("team_name", team_name)
        .gt("matches_checked", 0)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )

    if not rows:
        return 50

    return rows[0]["form_score"]


def main():
    games = (
        supabase.table("soccer_match_strength")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
        .data
    )

    saved = 0

    for game in games:
        home_form = float(get_latest_form(game["game_id"], game["home_team_name"]))
        away_form = float(get_latest_form(game["game_id"], game["away_team_name"]))

        diff = round(home_form - away_form, 2)

        row = {
            "game_id": game["game_id"],
            "home_team_name": game["home_team_name"],
            "away_team_name": game["away_team_name"],
            "home_team_home_form": home_form,
            "away_team_away_form": away_form,
            "home_away_difference": diff,
        }

        supabase.table("soccer_home_away_strength").insert(row).execute()
        saved += 1

    print(f"✅ Home/Away strength rows created: {saved}")


if __name__ == "__main__":
    main()
    