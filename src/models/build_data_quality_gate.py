from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def exists(table, game_id):
    rows = (
        supabase.table(table)
        .select("id")
        .eq("game_id", game_id)
        .limit(1)
        .execute()
        .data
    )
    return bool(rows)


def main():
    rows = (
        supabase.table("final_soccer_predictions")
        .select("*")
        .execute()
        .data
    )

    saved = 0

    for row in rows:
        game_id = row["game_id"]

        has_form = exists("soccer_match_strength", game_id)
        has_odds = row.get("odds_decimal") is not None
        has_lineup = exists("soccer_lineup_impact", game_id)
        has_injury = exists("soccer_injury_impact", game_id)

        score = 0

        if has_form:
            score += 35

        if has_odds:
            score += 30

        if has_lineup:
            score += 20

        if has_injury:
            score += 15

        confidence = float(row.get("confidence") or 0)
        edge = float(row.get("model_edge") or 0)

        allowed = (
            has_form
            and has_odds
            and confidence >= 60
            and edge >= 5
            and score >= 65
        )

        reasons = []

        if not has_form:
            reasons.append("missing form")

        if not has_odds:
            reasons.append("missing odds")

        if not has_lineup:
            reasons.append("missing lineup")

        if not has_injury:
            reasons.append("missing injury data")

        if edge < 5:
            reasons.append("edge below 5%")

        if confidence < 60:
            reasons.append("confidence below 60%")

        supabase.table("soccer_data_quality_gate").upsert(
            {
                "game_id": game_id,
                "home_team_name": row["home_team_name"],
                "away_team_name": row["away_team_name"],
                "has_form": has_form,
                "has_odds": has_odds,
                "has_lineup": has_lineup,
                "has_injury_data": has_injury,
                "quality_score": score,
                "allowed_for_premium": allowed,
                "block_reason": ", ".join(reasons),
            },
            on_conflict="game_id",
        ).execute()

        saved += 1

    print(f"✅ Data quality rows created: {saved}")


if __name__ == "__main__":
    main()
    