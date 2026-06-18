from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = (
        supabase.table("priority_leagues")
        .select("sport_key, league_id, league_name, country, priority, enabled")
        .eq("sport_key", "soccer")
        .order("priority")
        .execute()
    )

    print(f"Priority leagues found: {len(result.data)}")

    for row in result.data:
        print(
            f"{row['league_id']} | {row['league_name']} | {row['country']} | enabled={row['enabled']}"
        )


if __name__ == "__main__":
    main()
    