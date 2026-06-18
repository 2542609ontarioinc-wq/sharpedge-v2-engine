from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_best_odds(home, away, pick, market):
    odds_rows = (
        supabase.table("soccer_odds")
        .select("*")
        .ilike("home_team_name", home)
        .ilike("away_team_name", away)
        .order("odds_decimal", desc=True)
        .execute()
        .data
    )

    if market == "winner":
        matches = [
            r for r in odds_rows
            if r["market"] == "h2h"
            and r["selection"].lower() == pick.lower()
        ]
    elif market == "goals":
        if "Over" in pick:
            target = "Over"
        else:
            target = "Under"

        matches = [
            r for r in odds_rows
            if r["market"] == "totals"
            and r["selection"].lower() == target.lower()
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
        odds = get_best_odds(
            row["home_team_name"],
            row["away_team_name"],
            row["best_pick"],
            row["market"],
        )

        if not odds:
            continue

        fair_probability = float(row["confidence"])
        market_probability = float(odds["implied_probability"])

        edge = round(fair_probability - market_probability, 2)

        note = {
            "bookmaker": odds["bookmaker"],
            "odds_decimal": odds["odds_decimal"],
            "odds_american": odds["odds_american"],
            "market_implied_probability": odds["implied_probability"],
            "model_probability": row["confidence"],
            "edge": edge,
        }

        supabase.table("final_soccer_predictions").update(
            {
                "secondary_pick": str(note),
            }
        ).eq("id", row["id"]).execute()

        updated += 1

    print(f"✅ Final predictions updated with odds info: {updated}")


if __name__ == "__main__":
    main()
    