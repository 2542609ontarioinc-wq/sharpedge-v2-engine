import requests
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY, ODDS_API_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def decimal_to_american(decimal_odds):
    if not decimal_odds or decimal_odds <= 1:
        return None

    if decimal_odds >= 2:
        return int((decimal_odds - 1) * 100)

    return int(-100 / (decimal_odds - 1))
    


def implied_probability(decimal_odds):
    if not decimal_odds:
        return None
    return round((1 / decimal_odds) * 100, 2)


def main():
    url = "https://api.the-odds-api.com/v4/sports/soccer/odds"

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
    }

    response = requests.get(url, params=params, timeout=30)

    print("Status:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return

    data = response.json()

    saved = 0

    for event in data:
        home = event.get("home_team")
        away = event.get("away_team")

        game_rows = (
            supabase.table("games")
            .select("id")
            .eq("sport_key", "soccer")
            .ilike("home_team_name", home)
            .ilike("away_team_name", away)
            .limit(1)
            .execute()
            .data
        )

        game_id = game_rows[0]["id"] if game_rows else None

        for bookmaker in event.get("bookmakers", []):
            book = bookmaker.get("title")

            for market in bookmaker.get("markets", []):
                market_key = market.get("key")

                for outcome in market.get("outcomes", []):
                    price = outcome.get("price")
                    selection = outcome.get("name")
                    line = outcome.get("point")

                    row = {
                        "game_id": game_id,
                        "home_team_name": home,
                        "away_team_name": away,
                        "market": market_key,
                        "selection": selection,
                        "bookmaker": book,
                        "odds_decimal": price,
                        "odds_american": decimal_to_american(price) if price else None,
                        "implied_probability": implied_probability(price),
                        "line": line,
                    }

                    supabase.table("soccer_odds").insert(row).execute()
                    saved += 1

    print(f"✅ Soccer odds rows saved: {saved}")


if __name__ == "__main__":
    main()
    