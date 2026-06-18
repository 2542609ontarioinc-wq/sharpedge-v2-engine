from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_weather_features")
    .select("*")
    .order("created_at", desc=True)
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["home_team_name"],
        "vs",
        row["away_team_name"],
        "| Venue:",
        row.get("venue_name"),
        "| City:",
        row.get("venue_city"),
        "| Temp:",
        row.get("temperature_c"),
        "| Wind:",
        row.get("wind_kph"),
        "| Rain:",
        row.get("precipitation_mm"),
        "| Status:",
        row.get("weather_status"),
    )
    