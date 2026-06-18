import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
SPORTSDATA_KEY = os.getenv("SPORTSDATA_KEY")
APISPORTS_KEY = os.getenv("APISPORTS_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

TORONTO_TIMEZONE = "America/Toronto"

REQUIRED_KEYS = {
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_SERVICE_KEY": SUPABASE_SERVICE_KEY,
    "ODDS_API_KEY": ODDS_API_KEY,
    "SPORTSDATA_KEY": SPORTSDATA_KEY,
    "APISPORTS_KEY": APISPORTS_KEY,
    "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY,
}


def validate_settings():
    missing = [key for key, value in REQUIRED_KEYS.items() if not value]

    if missing:
        raise ValueError(
            f"Missing environment keys: {', '.join(missing)}"
        )

    return True
    