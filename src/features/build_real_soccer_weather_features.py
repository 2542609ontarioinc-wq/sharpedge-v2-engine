import requests
from datetime import datetime, timezone

from supabase import create_client
from src.config.settings import (
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
    OPENWEATHER_API_KEY,
)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_weather(city):
    if not city:
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(url, params=params, timeout=20)

        if response.status_code != 200:
            return None

        return response.json()

    except Exception:
        return None


def calculate_weather_scores(temp, humidity, wind_kph, rain_mm):
    risk = 0

    if temp is not None and (temp <= 0 or temp >= 32):
        risk += 20

    if humidity is not None and humidity >= 85:
        risk += 10

    if wind_kph is not None and wind_kph >= 25:
        risk += 25

    if rain_mm is not None and rain_mm >= 2:
        risk += 20

    goals_modifier = 0
    corners_modifier = 0

    if wind_kph is not None and wind_kph >= 25:
        goals_modifier -= 6
        corners_modifier += 5

    if rain_mm is not None and rain_mm >= 2:
        goals_modifier -= 5
        corners_modifier += 3

    if temp is not None and temp >= 32:
        goals_modifier -= 3

    return risk, goals_modifier, corners_modifier


def main():
    games = (
        supabase.table("games")
        .select("id, home_team_name, away_team_name, raw_json")
        .eq("sport_key", "soccer")
        .limit(5000)
        .execute()
        .data
    )

    saved = 0
    skipped = 0

    for game in games:
        raw = game.get("raw_json") or {}
        fixture = raw.get("fixture") or {}
        venue = fixture.get("venue") or {}

        city = venue.get("city")
        venue_name = venue.get("name")
        country = venue.get("country")

        weather = get_weather(city)

        if not weather:
            row = {
                "game_id": game["id"],
                "home_team_name": game["home_team_name"],
                "away_team_name": game["away_team_name"],
                "venue_name": venue_name,
                "venue_city": city,
                "venue_country": country,
                "weather_status": "weather_unavailable",
                "source": "openweather",
            }

            supabase.table("soccer_weather_features").upsert(
                row,
                on_conflict="game_id",
            ).execute()

            skipped += 1
            continue

        main_weather = weather.get("main", {})
        wind = weather.get("wind", {})
        rain = weather.get("rain", {})

        temp = main_weather.get("temp")
        humidity = main_weather.get("humidity")
        wind_kph = round((wind.get("speed") or 0) * 3.6, 2)
        rain_mm = rain.get("1h") or rain.get("3h") or 0

        risk, goals_modifier, corners_modifier = calculate_weather_scores(
            temp,
            humidity,
            wind_kph,
            rain_mm,
        )

        row = {
            "game_id": game["id"],
            "home_team_name": game["home_team_name"],
            "away_team_name": game["away_team_name"],
            "venue_name": venue_name,
            "venue_city": city,
            "venue_country": country,
            "temperature_c": temp,
            "humidity": humidity,
            "wind_kph": wind_kph,
            "precipitation_mm": rain_mm,
            "weather_risk_score": risk,
            "goals_weather_modifier": goals_modifier,
            "corners_weather_modifier": corners_modifier,
            "weather_status": "weather_available",
            "weather_fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "openweather",
        }

        supabase.table("soccer_weather_features").upsert(
            row,
            on_conflict="game_id",
        ).execute()

        saved += 1

    print(f"✅ Weather rows updated: {saved}")
    print(f"⚠️ Weather rows unavailable/skipped: {skipped}")


if __name__ == "__main__":
    main()
    