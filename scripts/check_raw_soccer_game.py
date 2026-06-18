from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("games")
        .select("home_team_name, away_team_name, league_key, external_game_id, raw_json")
        .eq("sport_key", "soccer")
        .eq("league_key", "1")
        .limit(1)
        .execute()
    )

    if not result.data:
        print("No game found")
        return

    row = result.data[0]
    raw = row.get("raw_json") or {}

    print("GAME:")
    print(row["home_team_name"], "vs", row["away_team_name"])
    print("league:", row["league_key"])
    print("fixture:", row["external_game_id"])

    print("\nRAW JSON KEYS:")
    print(list(raw.keys()))

    print("\nHAS enriched_details:")
    print("enriched_details" in raw)

    if "enriched_details" in raw:
        print("\nENRICHED KEYS:")
        print(list(raw["enriched_details"].keys()))


if __name__ == "__main__":
    main()
    