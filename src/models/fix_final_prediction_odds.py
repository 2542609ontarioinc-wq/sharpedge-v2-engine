from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_best_odds(row):
    odds_rows = (
        supabase.table("soccer_odds")
        .select("*")
        .eq("game_id", row["game_id"])
        .order("odds_decimal", desc=True)
        .execute()
        .data
    )

    if row["market"] == "winner":
        matches = [
            o for o in odds_rows
            if o["market"] == "h2h"
            and o["selection"].lower() == row["best_pick"].lower()
        ]
    elif row["market"] == "goals":
        target = "Over" if "Over" in row["best_pick"] else "Under"
        matches = [
            o for o in odds_rows
            if o["market"] == "totals"
            and o["selection"].lower() == target.lower()
        ]
    else:
        matches = []

    if not matches:
        return None

    return sorted(matches, key=lambda x: float(x["odds_decimal"]), reverse=True)[0]


def main():
    rows = (
        supabase.table("final_soccer_predictions")
        .select("*")
        .execute()
        .data
    )

    updated = 0

    for row in rows:
        odds = get_best_odds(row)

        if not odds:
            continue

        edge = round(float(row["confidence"]) - float(odds["implied_probability"]), 2)

        supabase.table("final_soccer_predictions").update(
            {
                "bookmaker": odds["bookmaker"],
                "odds_decimal": odds["odds_decimal"],
                "odds_american": odds["odds_american"],
                "market_implied_probability": odds["implied_probability"],
                "model_edge": edge,
            }
        ).eq("id", row["id"]).execute()

        updated += 1

    print(f"✅ Final prediction odds columns updated: {updated}")


if __name__ == "__main__":
    main()