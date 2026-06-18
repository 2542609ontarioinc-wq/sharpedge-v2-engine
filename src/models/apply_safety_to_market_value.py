from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    values = (
        supabase.table("soccer_market_value")
        .select("*")
        .execute()
        .data
    )

    flags = (
        supabase.table("soccer_model_safety_flags")
        .select("*")
        .execute()
        .data
    )

    flag_map = {row["game_id"]: row for row in flags}

    updated = 0

    for row in values:
        game_id = row["game_id"]
        flag = flag_map.get(game_id)

        if not flag:
            continue

        original_rating = float(row.get("value_rating") or 0)
        cap = float(flag.get("value_cap") or 100)

        capped_rating = min(original_rating, cap)

        if not flag.get("final_allowed"):
            capped_rating = min(capped_rating, 59)

        supabase.table("soccer_market_value").update(
            {
                "value_rating": round(capped_rating, 2),
            }
        ).eq("game_id", game_id).execute()

        updated += 1

    print(f"✅ Safety caps applied to market value rows: {updated}")


if __name__ == "__main__":
    main()