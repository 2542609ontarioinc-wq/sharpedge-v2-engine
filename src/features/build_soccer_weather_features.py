from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    games = (
        supabase.table("games")
        .select("id, home_team_name, away_team_name")
        .eq("sport_key", "soccer")
        .limit(1000)
        .execute()
        .data
    )

    saved = 0

    for game in games:
        # Placeholder until stadium/location weather API is connected.
        temperature = None
        humidity = None
        wind = None
        precipitation = None

        risk = 0
        goals_modifier = 0
        corners_modifier = 0

        row = {
            "game_id": game["id"],
            "home_team_name": game["home_team_name"],
            "away_team_name": game["away_team_name"],
            "temperature_c": temperature,
            "humidity": humidity,
            "wind_kph": wind,
            "precipitation_mm": precipitation,
            "weather_risk_score": risk,
            "goals_weather_modifier": goals_modifier,
            "corners_weather_modifier": corners_modifier,
            "source": "placeholder",
        }

        supabase.table("soccer_weather_features").upsert(
            row,
            on_conflict="game_id",
        ).execute()

        saved += 1

    print(f"✅ Weather feature rows upserted: {saved}")


if __name__ == "__main__":
    main()
    