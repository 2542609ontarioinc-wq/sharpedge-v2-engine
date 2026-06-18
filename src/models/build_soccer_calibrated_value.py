from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def num(value, default=0):
    try:
        return float(value)
    except Exception:
        return default


def tier(score):
    if score >= 85:
        return "Elite Value"
    if score >= 75:
        return "Strong Value"
    if score >= 65:
        return "Playable Value"
    if score >= 55:
        return "Lean Only"
    return "Pass"


def main():
    values = supabase.table("soccer_market_value").select("*").execute().data
    flags = supabase.table("soccer_model_safety_flags").select("*").execute().data
    features = supabase.table("soccer_match_features").select("*").execute().data
    matchups = supabase.table("soccer_matchup_features").select("*").execute().data

    flag_map = {row["game_id"]: row for row in flags}
    feature_map = {row["game_id"]: row for row in features}
    matchup_map = {row["game_id"]: row for row in matchups}

    saved = 0

    for value in values:
        game_id = value["game_id"]

        flag = flag_map.get(game_id, {})
        feature = feature_map.get(game_id, {})
        matchup = matchup_map.get(game_id, {})

        raw_rating = num(value.get("value_rating"))
        safety_score = num(flag.get("safety_score"))
        matchup_score = num(matchup.get("overall_matchup_score"))

        confidence = num(feature.get("best_confidence"))
        edge = num(value.get("edge"))
        ev = num(value.get("expected_value"))

        notes = []

        confidence_dampener = 1.0
        sample_dampener = 1.0

        if confidence >= 75:
            confidence_dampener -= 0.08
            notes.append("high confidence dampened until backtested")

        if raw_rating >= 95:
            confidence_dampener -= 0.12
            notes.append("raw value capped from extreme rating")

        if matchup_score < 60:
            sample_dampener -= 0.10
            notes.append("matchup score below 60")

        if safety_score < 90:
            sample_dampener -= 0.10
            notes.append("safety score below 90")

        if edge < 5:
            sample_dampener -= 0.10
            notes.append("edge below 5")

        if ev < 0.05:
            sample_dampener -= 0.10
            notes.append("EV below 5%")

        dampened = raw_rating * confidence_dampener * sample_dampener

        # Hard cap before long-term calibration data exists
        if raw_rating >= 95:
            dampened = min(dampened, 88)

        final_score = round(max(0, min(100, dampened)), 2)

        final_allowed = (
            bool(flag.get("final_allowed"))
            and final_score >= 65
            and edge >= 5
            and ev >= 0.05
        )

        row = {
            "game_id": game_id,
            "home_team_name": feature.get("home_team_name"),
            "away_team_name": feature.get("away_team_name"),
            "pick": feature.get("best_pick"),
            "market": value.get("market"),
            "bookmaker": value.get("bookmaker"),
            "raw_value_rating": raw_rating,
            "safety_score": safety_score,
            "matchup_score": matchup_score,
            "confidence_dampener": round(confidence_dampener, 2),
            "sample_dampener": round(sample_dampener, 2),
            "final_value_rating": final_score,
            "final_tier": tier(final_score),
            "final_allowed": final_allowed,
            "notes": ", ".join(notes),
        }

        supabase.table("soccer_calibrated_value").upsert(
            row,
            on_conflict="game_id",
        ).execute()

        saved += 1

    print(f"✅ Calibrated value rows upserted: {saved}")


if __name__ == "__main__":
    main()