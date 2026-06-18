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
        .limit(5000)
        .execute()
        .data
    )

    grouped = defaultdict(list)

    for row in rows:
        grouped[row["league_id"]].append(row)

    saved = 0

    for league_id, items in grouped.items():
        league_name = items[0].get("league_name")

        # team rows are 2 per match, so goals/corners/etc are per team row
        fixture_map = defaultdict(list)
        for item in items:
            fixture_map[item["fixture_id"]].append(item)

        matches_used = len(fixture_map)

        fixture_totals = []

        for fixture_id, teams in fixture_map.items():
            total_goals = sum(t["goals_for"] for t in teams)
            btts = all(t["goals_for"] > 0 for t in teams)
            over25 = total_goals > 2.5

            fixture_totals.append(
                {
                    "total_goals": total_goals,
                    "btts": btts,
                    "over25": over25,
                }
            )

        baseline = {
            "league_id": league_id,
            "league_name": league_name,
            "matches_used": matches_used,

            "avg_goals": avg([f["total_goals"] for f in fixture_totals]),
            "avg_shots": avg([r["shots_total"] for r in items]),
            "avg_shots_on_goal": avg([r["shots_on_goal"] for r in items]),
            "avg_possession": avg([r["possession_percent"] for r in items]),
            "avg_corners": avg([r["corners"] for r in items]),
            "avg_fouls": avg([r["fouls"] for r in items]),
            "avg_yellow_cards": avg([r["yellow_cards"] for r in items]),
            "avg_red_cards": avg([r["red_cards"] for r in items]),

            "btts_rate": round(
                sum(1 for f in fixture_totals if f["btts"]) * 100 / matches_used,
                2,
            )
            if matches_used
            else 0,
            "over_25_rate": round(
                sum(1 for f in fixture_totals if f["over25"]) * 100 / matches_used,
                2,
            )
            if matches_used
            else 0,
        }

        supabase.table("soccer_league_baselines").upsert(
            baseline,
            on_conflict="league_id",
        ).execute()

        saved += 1

    print(f"✅ League baselines upserted: {saved}")


if __name__ == "__main__":
    main()