from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY


KEYWORDS = [
    "World Cup",
    "World Cup Qualifiers",
    "Euro Championship",
    "UEFA Nations League",
    "Champions League",
    "Europa League",
    "Premier League",
    "La Liga",
    "Bundesliga",
    "Serie A",
    "Ligue 1",
    "Major League Soccer",
    "MLS",
    "Canadian Premier League",
    "Copa Libertadores",
]


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("games")
        .select("league_key, raw_json")
        .eq("sport_key", "soccer")
        .limit(2000)
        .execute()
    )

    found = {}

    for row in result.data:
        raw = row.get("raw_json") or {}
        league = raw.get("league") or {}

        league_id = league.get("id")
        league_name = league.get("name") or ""
        country = league.get("country") or ""

        text = f"{league_name} {country}".lower()

        for keyword in KEYWORDS:
            if keyword.lower() in text:
                key = f"{league_id} | {league_name} | {country}"
                found[key] = found.get(key, 0) + 1

    print("Priority leagues found:")
    print("----------------------")

    if not found:
        print("No priority leagues found in current saved games.")
        return

    for league, count in sorted(found.items()):
        print(f"{count} games | {league}")


if __name__ == "__main__":
    main()