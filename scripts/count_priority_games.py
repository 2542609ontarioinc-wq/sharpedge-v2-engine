from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    leagues_result = (
        supabase.table("priority_leagues")
        .select("league_id")
        .eq("sport_key", "soccer")
        .eq("enabled", True)
        .execute()
    )

    priority_ids = {row["league_id"] for row in leagues_result.data}

    games_result = (
        supabase.table("games")
        .select("league_key, home_team_name, away_team_name, game_date")
        .eq("sport_key", "soccer")
        .limit(5000)
        .execute()
    )

    total = len(games_result.data)
    priority_games = []
    ignored_games = []

    for game in games_result.data:
        if game["league_key"] in priority_ids:
            priority_games.append(game)
        else:
            ignored_games.append(game)

    print(f"Total soccer games: {total}")
    print(f"Priority games: {len(priority_games)}")
    print(f"Ignored games: {len(ignored_games)}")

    print("\nPriority games sample:")
    for game in priority_games[:20]:
        print(
            f"{game['home_team_name']} vs {game['away_team_name']} | {game['game_date']} | league={game['league_key']}"
        )


if __name__ == "__main__":
    main()