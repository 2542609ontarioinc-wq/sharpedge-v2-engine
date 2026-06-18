from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def choose_best_pick(row):
    candidates = [
        {
            "pick": row["winner_pick"],
            "market": "winner",
            "confidence": float(row["winner_confidence"]),
        },
        {
            "pick": row["goals_pick"],
            "market": "goals",
            "confidence": float(row["goals_confidence"]),
        },
        {
            "pick": row["btts_pick"],
            "market": "btts",
            "confidence": float(row["btts_confidence"]),
        },
    ]

    candidates = sorted(
        candidates,
        key=lambda x: x["confidence"],
        reverse=True,
    )

    return candidates[0], candidates[1]


def main():
    rows = (
        supabase.table("soccer_ensemble_predictions")
        .select("*")
        .order("ensemble_score", desc=True)
        .limit(100)
        .execute()
        .data
    )

    saved = 0

    for row in rows:
        best, second = choose_best_pick(row)

        final = {
            "game_id": row["game_id"],
            "home_team_name": row["home_team_name"],
            "away_team_name": row["away_team_name"],
            "best_pick": best["pick"],
            "market": best["market"],
            "confidence": best["confidence"],
            "secondary_pick": second["pick"],
            "secondary_market": second["market"],
            "secondary_confidence": second["confidence"],
            "value_rating": row["value_rating"],
            "ensemble_score": row["ensemble_score"],
        }

        supabase.table("final_soccer_predictions").upsert(final, on_conflict="game_id,market").execute()
        saved += 1

    print(f"✅ Final soccer predictions created: {saved}")


if __name__ == "__main__":
    main()
    