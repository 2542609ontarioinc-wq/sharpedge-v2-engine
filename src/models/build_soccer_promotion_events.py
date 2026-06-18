from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    rows = (
        supabase.table("soccer_elite_score")
        .select("*")
        .execute()
        .data
    )

    created = 0

    for row in rows:
        game_id = row["game_id"]

        previous = (
            supabase.table("soccer_pick_current_status")
            .select("*")
            .eq("game_id", game_id)
            .eq("market", row["market"])
            .eq("pick", row["pick"])
            .limit(1)
            .execute()
            .data
        )

        old = previous[0] if previous else None

        old_status = old.get("publish_status") if old else None
        new_status = row.get("publish_status")

        old_tier = old.get("elite_tier") if old else None
        new_tier = row.get("elite_tier")

        if old and old_status != new_status:
            message = (
                f'{row["home_team_name"]} vs {row["away_team_name"]} '
                f'{row["pick"]} moved from {old_status} to {new_status}. '
                f'Elite Score: {row["elite_score"]}.'
            )

            event = {
                "game_id": game_id,
                "home_team_name": row.get("home_team_name"),
                "away_team_name": row.get("away_team_name"),
                "pick": row.get("pick"),
                "market": row.get("market"),
                "old_status": old_status,
                "new_status": new_status,
                "old_tier": old_tier,
                "new_tier": new_tier,
                "elite_score": row.get("elite_score"),
                "safety_score_v3": row.get("safety_score_v3"),
                "message": message,
            }

            supabase.table("soccer_pick_status_events").insert(event).execute()
            print("🚨", message)
            created += 1

        current = {
            "game_id": game_id,
            "home_team_name": row.get("home_team_name"),
            "away_team_name": row.get("away_team_name"),
            "pick": row.get("pick"),
            "market": row.get("market"),
            "publish_status": row.get("publish_status"),
            "elite_tier": row.get("elite_tier"),
            "elite_score": row.get("elite_score"),
            "safety_score_v3": row.get("safety_score_v3"),
        }

        supabase.table("soccer_pick_current_status").upsert(
            current,
            on_conflict="game_id,market,pick",
        ).execute()

    print(f"✅ Promotion events created: {created}")


if __name__ == "__main__":
    main()
    