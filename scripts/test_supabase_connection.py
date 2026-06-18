from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY, validate_settings


def main():
    validate_settings()

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    response = supabase.table("sports").select("*").limit(10).execute()

    print("✅ Supabase connection successful")
    print(f"✅ Sports rows found: {len(response.data)}")
    print(response.data)


if __name__ == "__main__":
    main()
    