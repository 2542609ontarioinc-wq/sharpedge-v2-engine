from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY


def calculate_basic_soccer_features(game):
    raw = game.get("raw_json") or {}
    league = raw.get("league") or {}
    fixture = raw.get("fixture") or {}
    teams = raw.get("teams") or {}
    goals = raw.get("goals") or {}
    status = fixture.get("status") or {}

    home = teams.get("home") or {}
    away = teams.get("away") or {}

    team_features = {
        "home_team": home.get("name"),
        "away_team": away.get("name"),
        "home_winner_flag": home.get("winner"),
        "away_winner_flag": away.get("winner"),
        "home_score": goals.get("home"),
        "away_score": goals.get("away"),
    }

    context_features = {
        "league_id": league.get("id"),
        "league_name": league.get("name"),
        "country": league.get("country"),
        "season": league.get("season"),
        "round": league.get("round"),
        "venue": (fixture.get("venue") or {}).get("name"),
        "city": (fixture.get("venue") or {}).get("city"),
        "status_short": status.get("short"),
        "status_long": status.get("long"),
    }

    market_features = {}

    player_features = {}

    data_quality_score = 35

    if game.get("start_time_toronto"):
        data_quality_score += 10

    if context_features.get("league_name"):
        data_quality_score += 10

    if context_features.get("venue"):
        data_quality_score += 10

    if team_features.get("home_team") and team_features.get("away_team"):
        data_quality_score += 10

    if context_features.get("status_short"):
        data_quality_score += 5

    return {
        "game_id": game["id"],
        "sport_key": "soccer",
        "feature_version": "soccer_basic_v1",
        "team_features": team_features,
        "player_features": player_features,
        "market_features": market_features,
        "context_features": context_features,
        "data_quality_score": min(data_quality_score, 100),
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
        .select("*")
        .eq("sport_key", "soccer")
        .in_("league_key", priority_ids)
        .limit(500)
        .execute()
    )

    games = games_result.data or []

    print(f"Priority soccer games found: {len(games)}")

    saved = 0

    for game in games:
        feature_data = calculate_basic_soccer_features(game)

        supabase.table("model_features").insert(feature_data).execute()
        saved += 1

    print(f"✅ Soccer feature rows created: {saved}")


if __name__ == "__main__":
    main()
    