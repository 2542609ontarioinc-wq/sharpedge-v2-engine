from collections import defaultdict

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


WEIGHTS = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]


def weighted_avg(matches, field):
    total_weight = 0
    total_value = 0

    for index, match in enumerate(matches[:10]):
        weight = WEIGHTS[index]
        value = float(match.get(field) or 0)

        total_value += value * weight
        total_weight += weight

    return round(total_value / total_weight, 2) if total_weight else 0


def simple_avg(matches, field):
    if not matches:
        return 0

    values = [float(match.get(field) or 0) for match in matches]
    return round(sum(values) / len(values), 2)


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
        recent = matches[:10]

        home_matches = [m for m in recent if m.get("is_home")]
        away_matches = [m for m in recent if not m.get("is_home")]

        weighted_goals_for = weighted_avg(recent, "goals_for")
        weighted_goals_against = weighted_avg(recent, "goals_against")
        weighted_shots_total = weighted_avg(recent, "shots_total")
        weighted_shots_on_goal = weighted_avg(recent, "shots_on_goal")
        weighted_possession = weighted_avg(recent, "possession_percent")
        weighted_corners = weighted_avg(recent, "corners")
        weighted_fouls = weighted_avg(recent, "fouls")
        weighted_yellow_cards = weighted_avg(recent, "yellow_cards")

        attack_index = round(
            (weighted_goals_for * 28)
            + (weighted_shots_on_goal * 9)
            + (weighted_shots_total * 2.2),
            2,
        )

        defense_index = round(
            100
            - (weighted_goals_against * 28)
            - (weighted_shots_total * 1.1),
            2,
        )

        cards_index = round(
            (weighted_fouls * 2.5)
            + (weighted_yellow_cards * 13),
            2,
        )

        corners_index = round(
            (weighted_corners * 11)
            + (weighted_shots_total * 1.6),
            2,
        )

        row = {
            "team_name": team_name,
            "matches_used": len(recent),

            "weighted_goals_for": weighted_goals_for,
            "weighted_goals_against": weighted_goals_against,
            "weighted_shots_total": weighted_shots_total,
            "weighted_shots_on_goal": weighted_shots_on_goal,
            "weighted_possession": weighted_possession,
            "weighted_corners": weighted_corners,
            "weighted_fouls": weighted_fouls,
            "weighted_yellow_cards": weighted_yellow_cards,

            "home_goals_for": simple_avg(home_matches, "goals_for"),
            "home_goals_against": simple_avg(home_matches, "goals_against"),
            "home_shots_total": simple_avg(home_matches, "shots_total"),
            "home_corners": simple_avg(home_matches, "corners"),

            "away_goals_for": simple_avg(away_matches, "goals_for"),
            "away_goals_against": simple_avg(away_matches, "goals_against"),
            "away_shots_total": simple_avg(away_matches, "shots_total"),
            "away_corners": simple_avg(away_matches, "corners"),

            "attack_index": attack_index,
            "defense_index": defense_index,
            "cards_index": cards_index,
            "corners_index": corners_index,
        }

        supabase.table("soccer_team_advanced_rolling_features").upsert(
            row,
            on_conflict="team_name",
        ).execute()

        saved += 1

    print(f"✅ Advanced rolling features upserted: {saved}")


if __name__ == "__main__":
    main()
    