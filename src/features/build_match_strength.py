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
        supabase.table("games")
        .select("id, home_team_name, away_team_name, league_key")
        .eq("sport_key", "soccer")
        .in_("league_key", ["1", "479"])
        .execute()
        .data
    )

    saved = 0

    for game in games:
        home_score = get_latest_form(game["id"], game["home_team_name"])
        away_score = get_latest_form(game["id"], game["away_team_name"])

        diff = round(home_score - away_score, 2)

        if diff >= 20:
            edge = "home_strong_edge"
        elif diff <= -20:
            edge = "away_strong_edge"
        elif diff >= 8:
            edge = "home_small_edge"
        elif diff <= -8:
            edge = "away_small_edge"
        else:
            edge = "balanced"

        row = {
            "game_id": game["id"],
            "home_team_name": game["home_team_name"],
            "away_team_name": game["away_team_name"],
            "home_form_score": home_score,
            "away_form_score": away_score,
            "form_difference": diff,
            "predicted_edge": edge,
        }

        supabase.table("soccer_match_strength").insert(row).execute()
        saved += 1

    print(f"✅ Match strength rows created: {saved}")


if __name__ == "__main__":
    main()