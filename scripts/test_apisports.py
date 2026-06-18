import requests
from src.config.settings import APISPORTS_KEY, validate_settings


def main():
    validate_settings()

    url = "https://v3.football.api-sports.io/status"

    headers = {
        "x-apisports-key": APISPORTS_KEY
    }

    response = requests.get(url, headers=headers)

    print("Status:", response.status_code)
    print(response.text[:1000])


if __name__ == "__main__":
    main()
    