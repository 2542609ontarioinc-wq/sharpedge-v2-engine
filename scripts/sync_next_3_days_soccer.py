from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.ingestion.sync_soccer_games import sync_soccer_games_for_date


def main():
    today = datetime.now(ZoneInfo("America/Toronto")).date()

    for i in range(0, 4):
        date_str = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        print("Syncing:", date_str)
        sync_soccer_games_for_date(date_str)


if __name__ == "__main__":
    main()
    