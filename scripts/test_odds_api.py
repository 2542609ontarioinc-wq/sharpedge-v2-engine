import requests
from src.config.settings import ODDS_API_KEY, validate_settings


def main():
    validate_settings()

    url = "https://api.the-odds-api.com/v4/sports"
    params = {"apiKey": ODDS_API_KEY}

    response = requests.get(url, params=params)

    print("Status:", response.status_code)
    print(response.text[:1000])


if __name__ == "__main__":
    main()
    