from collections import defaultdict
from statistics import mean

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def avg(values):
    return round(mean(values), 2) if values else 0


def main():
    history = (
        supabase.table("soccer_team_stat_history")
        .select("*")
        .order("game_date", desc=True)
        .limit(5000)
        .execute()
        .data
    )

    ratings = (
        supabase.table("soccer_team_advanced_rolling_features")
        .select("*")
        .execute()
        .data
    )

    rating_map = {r["team_name"]: r for r in ratings}
    grouped = defaultdict(list)

    for row in history:
        grouped[row["team_name"]].append(row)

    saved = 0

    for team_name, matches in grouped.items():
        recent = matches[:10]

        opponent_attacks = []
        opponent_defenses = []

        for match in recent:
            opponent = match["opponent_team_name"]
            opponent_rating = rating_map.get(opponent)

            if not opponent_rating:
                continue

            opponent_attacks.append(float(opponent_rating.get("attack_index") or 0))
            opponent_defenses.append(float(opponent_rating.get("defense_index") or 0))

        avg_opp_attack = avg(opponent_attacks)
        avg_opp_defense = avg(opponent_defenses)

        team_rating = rating_map.get(team_name, {})

        team_attack = float(team_rating.get("attack_index") or 0)
        team_defense = float(team_rating.get("defense_index") or 0)

        strength_of_schedule = round((avg_opp_attack + avg_opp_defense) / 2, 2)

        adjusted_attack = round(team_attack + (strength_of_schedule * 0.10), 2)
        adjusted_defense = round(team_defense + (avg_opp_attack * 0.05), 2)

        row = {
            "team_name": team_name,
            "matches_used": len(recent),
            "avg_opponent_attack": avg_opp_attack,
            "avg_opponent_defense": avg_opp_defense,
            "strength_of_schedule": strength_of_schedule,
            "adjusted_attack_index": adjusted_attack,
            "adjusted_defense_index": adjusted_defense,
        }

        supabase.table("soccer_opponent_strength").upsert(
            row,
            on_conflict="team_name",
        ).execute()

        saved += 1

    print(f"✅ Opponent strength rows upserted: {saved}")


if __name__ == "__main__":
    main()