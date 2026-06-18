from functools import reduce
from operator import mul

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def combined_probability(confidences):
    decimals = [float(c) / 100 for c in confidences]
    combined = reduce(mul, decimals, 1)
    return round(combined * 100, 2)


def risk_level(prob):
    if prob >= 45:
        return "Low"
    if prob >= 30:
        return "Medium"
    return "High"


def build_parlay(rows, parlay_type, count):
    legs = rows[:count]

    if len(legs) < count:
        return None

    confidences = [leg["confidence"] for leg in legs]
    combined = combined_probability(confidences)

    return {
        "parlay_type": parlay_type,
        "legs": [
            {
                "game": f"{leg['home_team_name']} vs {leg['away_team_name']}",
                "pick": leg["best_pick"],
                "market": leg["market"],
                "confidence": leg["confidence"],
                "tier": leg["tier"],
            }
            for leg in legs
        ],
        "combined_confidence": combined,
        "risk_level": risk_level(combined),
    }


def main():
    rows = (
        supabase.table("soccer_premium_rankings")
        .select("*")
        .neq("tier", "Pass")
        .order("rank")
        .execute()
        .data
    )

    parlays = [
        build_parlay(rows, "safe_2_leg", 2),
        build_parlay(rows, "safe_3_leg", 3),
    ]

    saved = 0

    for parlay in parlays:
        if not parlay:
            continue

        supabase.table("soccer_parlays").insert(parlay).execute()
        saved += 1

    print(f"✅ Parlays created: {saved}")


if __name__ == "__main__":
    main()
    