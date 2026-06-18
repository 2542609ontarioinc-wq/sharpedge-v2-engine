from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def num(value, default=0):
    try:
        return float(value)
    except Exception:
        return default


def main():
    features = (
        supabase.table("soccer_match_features")
        .select("*")
        .limit(5000)
        .execute()
        .data
    )

    saved = 0

    for row in features:
        notes = []
        safety_score = 100
        value_cap = 100

        sample_size_risk = False
        missing_odds_risk = row.get("odds_decimal") is None
        missing_weather_risk = row.get("temperature_c") is None
        extreme_model_risk = False

        home_attack = num(row.get("home_adjusted_attack_index"))
        away_attack = num(row.get("away_adjusted_attack_index"))
        home_defense = num(row.get("home_adjusted_defense_index"))
        away_defense = num(row.get("away_adjusted_defense_index"))

        confidence = num(row.get("best_confidence"))
        edge = num(row.get("model_edge"))

        if home_attack >= 250 or away_attack >= 250:
            sample_size_risk = True
            extreme_model_risk = True
            safety_score -= 25
            value_cap = min(value_cap, 75)
            notes.append("extreme attack index likely caused by small sample")

        if home_defense <= 0 or away_defense <= 0:
            sample_size_risk = True
            extreme_model_risk = True
            safety_score -= 20
            value_cap = min(value_cap, 75)
            notes.append("extreme defense index likely caused by small sample")

        if missing_odds_risk:
            safety_score -= 30
            value_cap = min(value_cap, 60)
            notes.append("missing market odds")

        if missing_weather_risk:
            safety_score -= 5
            notes.append("missing weather")

        if confidence >= 80 and edge <= 0:
            extreme_model_risk = True
            safety_score -= 15
            value_cap = min(value_cap, 80)
            notes.append("high confidence without positive market edge")

        final_allowed = (
            safety_score >= 70
            and not missing_odds_risk
            and not extreme_model_risk
        )

        out = {
            "game_id": row["game_id"],
            "home_team_name": row["home_team_name"],
            "away_team_name": row["away_team_name"],
            "sample_size_risk": sample_size_risk,
            "missing_odds_risk": missing_odds_risk,
            "missing_weather_risk": missing_weather_risk,
            "extreme_model_risk": extreme_model_risk,
            "safety_score": max(0, safety_score),
            "value_cap": value_cap,
            "final_allowed": final_allowed,
            "safety_notes": ", ".join(notes),
        }

        supabase.table("soccer_model_safety_flags").upsert(
            out,
            on_conflict="game_id",
        ).execute()

        saved += 1

    print(f"✅ Soccer model safety flags upserted: {saved}")


if __name__ == "__main__":
    main()