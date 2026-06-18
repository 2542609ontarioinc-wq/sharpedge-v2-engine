from datetime import datetime, date

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def parse_date(value):
    if not value:
        return None

    if isinstance(value, date):
        return value

    return datetime.fromisoformat(str(value)[:10]).date()


def team_history(team_name):
    rows = (
        supabase.table("soccer_team_stat_history")
        .select("*")
        .eq("team_name", team_name)
        .order("game_date", desc=True)
        .limit(20)
        .execute()
        .data
    )
    return rows


def days_rest(game_date, history):
    gd = parse_date(game_date)

    if not gd or not history:
        return None

    previous_dates = []

    for row in history:
        d = parse_date(row.get("game_date"))
        if d and d < gd:
            previous_dates.append(d)

    if not previous_dates:
        return None

    last_match = max(previous_dates)
    return (gd - last_match).days


def matches_in_window(game_date, history, days):
    gd = parse_date(game_date)

    if not gd:
        return 0

    count = 0

    for row in history:
        d = parse_date(row.get("game_date"))

        if d and d < gd and (gd - d).days <= days:
            count += 1

    return count


def main():
    games = (
        supabase.table("games")
        .select("id, home_team_name, away_team_name, game_date")
        .eq("sport_key", "soccer")
        .limit(1000)
        .execute()
        .data
    )

    saved = 0

    for game in games:
        home = game["home_team_name"]
        away = game["away_team_name"]
        game_date = game.get("game_date")

        home_history = team_history(home)
        away_history = team_history(away)

        home_rest = days_rest(game_date, home_history)
        away_rest = days_rest(game_date, away_history)

        home_7 = matches_in_window(game_date, home_history, 7)
        away_7 = matches_in_window(game_date, away_history, 7)

        home_14 = matches_in_window(game_date, home_history, 14)
        away_14 = matches_in_window(game_date, away_history, 14)

        rest_advantage = 0

        if home_rest is not None and away_rest is not None:
            rest_advantage = home_rest - away_rest

        congestion_score = (home_7 + away_7) * 8 + (home_14 + away_14) * 3

        # Placeholder until we add stadium/team coordinates.
        travel_fatigue = 0

        row = {
            "game_id": game["id"],
            "home_team_name": home,
            "away_team_name": away,
            "home_days_rest": home_rest,
            "away_days_rest": away_rest,
            "home_matches_last_7": home_7,
            "away_matches_last_7": away_7,
            "home_matches_last_14": home_14,
            "away_matches_last_14": away_14,
            "rest_advantage": rest_advantage,
            "congestion_score": congestion_score,
            "travel_fatigue_score": travel_fatigue,
        }

        supabase.table("soccer_rest_travel_features").upsert(
            row,
            on_conflict="game_id",
        ).execute()

        saved += 1

    print(f"✅ Rest/travel feature rows upserted: {saved}")


if __name__ == "__main__":
    main()