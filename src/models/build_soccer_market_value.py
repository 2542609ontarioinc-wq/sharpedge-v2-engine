from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def num(value, default=0):
    try:
        return float(value)
    except Exception:
        return default


def kelly_fraction(decimal_odds, model_prob):
    b = decimal_odds - 1
    p = model_prob
    q = 1 - p

    if b <= 0:
        return 0

    kelly = ((b * p) - q) / b
    return round(max(0, kelly), 4)


def value_rating(edge, ev, kelly):
    score = 50
    score += edge * 1.2
    score += ev * 40
    score += kelly * 20
    return round(max(0, min(100, score)), 2)


def main():
    rows = (
        supabase.table("soccer_match_features")
        .select("*")
        .not_.is_("odds_decimal", "null")
        .limit(5000)
        .execute()
        .data
    )

    saved = 0

    for row in rows:
        odds = num(row.get("odds_decimal"))
        model_probability = num(row.get("best_confidence")) / 100

        if odds <= 1 or model_probability <= 0:
            continue

        implied_probability = round((1 / odds) * 100, 2)
        edge = round((model_probability * 100) - implied_probability, 2)

        ev = round((odds * model_probability) - 1, 4)
        kelly = kelly_fraction(odds, model_probability)

        rating = value_rating(edge, ev, kelly)

        out = {
            "game_id": row["game_id"],
            "bookmaker": row.get("bookmaker"),
            "market": row.get("best_market"),
            "model_probability": round(model_probability * 100, 2),
            "implied_probability": implied_probability,
            "edge": edge,
            "expected_value": ev,
            "kelly_fraction": kelly,
            "value_rating": rating,
        }

        supabase.table("soccer_market_value").upsert(
            out,
            on_conflict="game_id",
        ).execute()

        saved += 1

    print(f"✅ Soccer market value rows upserted: {saved}")


if __name__ == "__main__":
    main()