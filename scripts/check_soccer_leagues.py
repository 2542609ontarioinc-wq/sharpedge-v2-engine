from collections import Counter
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("games")
        .select("league_key, raw_json")
        .eq("sport_key", "soccer")
        .limit(1000)
        .execute()
    )

    leagues = []

    for row in result.data:
        raw = row.get("raw_json") or {}
        league = raw.get("league") or {}

        league_id = league.get("id")
        league_name = league.get("name")
        country = league.get("country")

        leagues.append(f"{league_id} | {league_name} | {country}")

    counts = Counter(leagues)

    print("Soccer leagues found:")
    print("---------------------")

    for league, count in counts.most_common():
        print(f"{count} games | {league}")


if __name__ == "__main__":
    main()