from collections import defaultdict
from statistics import mean

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def avg(values):
    return round(mean(values), 2) if values else 0


def style_label(attack, defense, cards, corners):
    if attack >= 130 and corners >= 80:
        return "High Attack / Corner Pressure"

    if defense >= 65:
        return "Defensive"

    if cards >= 65:
        return "Physical / Card Risk"

    if attack >= 110:
        return "Attacking"

    return "Balanced"


def main():
    rows = (
        supabase.table("soccer_team_stat_history")
        .select("*")
        .order("game_date", desc=True)
        .limit(5000)
        .execute()
        .data
    )

    grouped = defaultdict(list)

    for row in rows:
        grouped[row["team_name"]].append(row)

    saved = 0

    for team_name, matches in grouped.items():
        recent = matches[:5]

        goals_for = avg([m.get("goals_for") or 0 for m in recent])
        goals_against = avg([m.get("goals_against") or 0 for m in recent])
        shots = avg([m.get("shots_total") or 0 for m in recent])
        sog = avg([m.get("shots_on_goal") or 0 for m in recent])
        corners = avg([m.get("corners") or 0 for m in recent])
        fouls = avg([m.get("fouls") or 0 for m in recent])
        yellows = avg([m.get("yellow_cards") or 0 for m in recent])

        attack = round((goals_for * 28) + (sog * 9) + (shots * 2.2), 2)
        defense = round(100 - (goals_against * 28) - (shots * 1.1), 2)
        cards = round((fouls * 2.5) + (yellows * 13), 2)
        corner_index = round((corners * 11) + (shots * 1.6), 2)

        row = {
            "team_name": team_name,
            "matches_used": len(recent),
            "fallback_attack_index": attack,
            "fallback_defense_index": defense,
            "fallback_cards_index": cards,
            "fallback_corners_index": corner_index,
            "fallback_style_label": style_label(
                attack,
                defense,
                cards,
                corner_index,
            ),
        }

        supabase.table("soccer_team_profile_fallbacks").upsert(
            row,
            on_conflict="team_name",
        ).execute()

        saved += 1

    print(f"✅ Team profile fallback rows upserted: {saved}")


if __name__ == "__main__":
    main()
    