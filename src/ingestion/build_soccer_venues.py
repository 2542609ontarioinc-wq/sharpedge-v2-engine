from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    games = (
        supabase.table("games")
        .select("raw_json")
        .eq("sport_key", "soccer")
        .limit(5000)
        .execute()
        .data
    )

    saved = 0

    for game in games:
        raw = game.get("raw_json") or {}
        fixture = raw.get("fixture") or {}
        venue = fixture.get("venue") or {}

        venue_id = venue.get("id")

        if not venue_id:
            continue

        row = {
            "venue_id": str(venue_id),
            "venue_name": venue.get("name"),
            "city": venue.get("city"),
            "country": venue.get("country"),
            "capacity": venue.get("capacity"),
            "surface": venue.get("surface"),
        }

        supabase.table("soccer_venues").upsert(
            row,
            on_conflict="venue_id",
        ).execute()

        saved += 1

    print(f"✅ Soccer venues upserted: {saved}")


if __name__ == "__main__":
    main()
    