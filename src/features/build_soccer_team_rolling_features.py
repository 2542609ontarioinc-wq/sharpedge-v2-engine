from collections import defaultdict
from statistics import mean

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def avg(values):
    return round(mean(values), 2) if values else 0


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

        goals_for = avg([m["goals_for"] for m in recent])
        goals_against = avg([m["goals_against"] for m in recent])

        shots = avg([m["shots_total"] for m in recent])
        sog = avg([m["shots_on_goal"] for m in recent])
        possession = avg([m["possession_percent"] for m in recent])

        corners = avg([m["corners"] for m in recent])
        fouls = avg([m["fouls"] for m in recent])
        yellow = avg([m["yellow_cards"] for m in recent])
        red = avg([m["red_cards"] for m in recent])

        attacking_score = round((goals_for * 25) + (sog * 8) + (shots * 2), 2)
        defensive_score = round(100 - ((goals_against * 25) + (shots * 1.2)), 2)
        discipline_risk = round((fouls * 2.5) + (yellow * 12) + (red * 25), 2)
        corner_pressure = round((corners * 10) + (shots * 1.5), 2)

        row = {
            "team_name": team_name,
            "matches_used": len(recent),

            "avg_goals_for": goals_for,
            "avg_goals_against": goals_against,

            "avg_shots_total": shots,
            "avg_shots_on_goal": sog,

            "avg_possession": possession,

            "avg_corners": corners,
            "avg_fouls": fouls,
            "avg_yellow_cards": yellow,
            "avg_red_cards": red,

            "attacking_score": attacking_score,
            "defensive_score": defensive_score,
            "discipline_risk_score": discipline_risk,
            "corner_pressure_score": corner_pressure,
        }

        supabase.table("soccer_team_rolling_features").insert(row).execute()
        saved += 1

    print(f"✅ Rolling team feature rows created: {saved}")


if __name__ == "__main__":
    main()
    