from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def tier(row):
    score = float(row["ensemble_score"])
    conf = float(row["confidence"])

    if score >= 65 and conf >= 70:
        return "Elite"
    if score >= 58 and conf >= 65:
        return "Strong"
    if score >= 52 and conf >= 60:
        return "Playable"
    return "Pass"


def main():
    rows = (
        supabase.table("final_soccer_predictions")
        .select("*")
        .order("ensemble_score", desc=True)
        .execute()
        .data
    )

    saved = 0

    for index, row in enumerate(rows, start=1):
        out = {
            "rank": index,
            "game_id": row["game_id"],
            "home_team_name": row["home_team_name"],
            "away_team_name": row["away_team_name"],
            "best_pick": row["best_pick"],
            "market": row["market"],
            "confidence": row["confidence"],
            "ensemble_score": row["ensemble_score"],
            "value_rating": row["value_rating"],
            "tier": tier(row),
        }

        supabase.table("soccer_premium_rankings").upsert(out, on_conflict="game_id").execute()
        saved += 1

    print(f"✅ Premium rankings created: {saved}")


if __name__ == "__main__":
    main()
    