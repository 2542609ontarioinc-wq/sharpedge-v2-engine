from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TABLES = [
    "soccer_match_strength",
    "soccer_prediction_versions",
    "soccer_goals_prediction_versions",
    "soccer_btts_prediction_versions",
    "soccer_ensemble_predictions",
    "final_soccer_predictions",
    "soccer_premium_rankings",
]


def clean_table(table):
    rows = (
        supabase.table(table)
        .select("id, game_id, created_at")
        .order("created_at", desc=True)
        .execute()
        .data
    )

    seen = set()
    delete_ids = []

    for row in rows:
        game_id = row.get("game_id")

        if game_id in seen:
            delete_ids.append(row["id"])
        else:
            seen.add(game_id)

    for delete_id in delete_ids:
        supabase.table(table).delete().eq("id", delete_id).execute()

    print(f"{table}: deleted {len(delete_ids)} duplicates")


def main():
    for table in TABLES:
        clean_table(table)

    print("✅ Soccer duplicates cleaned")


if __name__ == "__main__":
    main()
    