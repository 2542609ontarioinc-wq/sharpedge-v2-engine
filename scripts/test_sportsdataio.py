import requests
from src.config.settings import SPORTSDATA_KEY, validate_settings


def main():
    validate_settings()

    url = f"https://api.sportsdata.io/v3/mlb/scores/json/Teams"

    headers = {
        "Ocp-Apim-Subscription-Key": SPORTSDATA_KEY
    }

    response = requests.get(url, headers=headers)

    print("Status:", response.status_code)
    print(response.text[:1000])


if __name__ == "__main__":
    main()
    