from collections import defaultdict
from statistics import mean

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def avg(values):
    return round(mean(values), 2) if values else 0


def main():
    results = (
        supabase.table("soccer_historical_results")
        .select("*")
        .limit(5000)
        .execute()
        .data
    )

    stat_rows = (
        supabase.table("soccer_team_stat_history")
        .select("*")
        .limit(5000)
        .execute()
        .data
    )

    stats_by_fixture = defaultdict(list)

    for row in stat_rows:
        stats_by_fixture[row["fixture_id"]].append(row)

    grouped = defaultdict(list)

    for result in results:
        raw = result.get("raw_json") or {}
        fixture = raw.get("fixture") or {}
        referee = fixture.get("referee")

        if not referee:
            continue

        teams = stats_by_fixture.get(result["fixture_id"], [])

        total_yellow = sum(t.get("yellow_cards") or 0 for t in teams)
        total_red = sum(t.get("red_cards") or 0 for t in teams)
        total_fouls = sum(t.get("fouls") or 0 for t in teams)
        total_corners = sum(t.get("corners") or 0 for t in teams)
        total_goals = (result.get("home_score") or 0) + (result.get("away_score") or 0)

        grouped[referee].append(
            {
                "yellow": total_yellow,
                "red": total_red,
                "fouls": total_fouls,
                "corners": total_corners,
                "goals": total_goals,
            }
        )

    saved = 0

    for referee, matches in grouped.items():
        yellow = avg([m["yellow"] for m in matches])
        red = avg([m["red"] for m in matches])
        fouls = avg([m["fouls"] for m in matches])
        corners = avg([m["corners"] for m in matches])
        goals = avg([m["goals"] for m in matches])

        strictness = round((yellow * 14) + (red * 30) + (fouls * 1.5), 2)
        flow = round(100 - strictness + (goals * 5), 2)

        row = {
            "referee_name": referee,
            "matches_used": len(matches),
            "avg_yellow_cards": yellow,
            "avg_red_cards": red,
            "avg_fouls": fouls,
            "avg_corners": corners,
            "avg_goals": goals,
            "card_strictness_score": strictness,
            "game_flow_score": flow,
        }

        supabase.table("soccer_referee_history").upsert(
            row,
            on_conflict="referee_name",
        ).execute()

        saved += 1

    print(f"✅ Referee history rows upserted: {saved}")


if __name__ == "__main__":
    main()