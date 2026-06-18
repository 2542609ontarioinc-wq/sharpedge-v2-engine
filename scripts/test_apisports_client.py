from datetime import datetime
from zoneinfo import ZoneInfo

from src.ingestion.apisports_client import APISportsClient


def main():
    client = APISportsClient()

    toronto_today = datetime.now(ZoneInfo("America/Toronto")).strftime("%Y-%m-%d")

    print("Testing API-Sports client...")
    print("Toronto date:", toronto_today)

    soccer = client.get_soccer_fixtures_by_date(toronto_today)
    soccer_count = len(soccer.get("response", []))
    print("Soccer fixtures found:", soccer_count)

    baseball = client.get_baseball_games_by_date(toronto_today)
    baseball_count = len(baseball.get("response", []))
    print("Baseball games found:", baseball_count)

    print("✅ API-Sports client test complete")


if __name__ == "__main__":
    main()
    