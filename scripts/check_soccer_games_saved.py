from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY


def main():
    supabase = create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_KEY,
    )

    result = (
        supabase.table("games")
        .select("sport_key,home_team_name,away_team_name,game_date")
        .eq("sport_key", "soccer")
        .limit(10)
        .execute()
    )

    print(f"Rows found: {len(result.data)}")

    for row in result.data:
        print(
            f"{row['home_team_name']} vs {row['away_team_name']} | {row['game_date']}"
        )


if __name__ == "__main__":
    main()
    