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
        "| Temp:",
        row["temperature_c"],
        "| Wind:",
        row["wind_kph"],
        "| Rain:",
        row["precipitation_mm"],
        "| Risk:",
        row["weather_risk_score"],
        "| Source:",
        row["source"],
    )
    