from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_stat_value(stats, stat_name):
    for item in stats:
        if item.get("type") == stat_name:
            value = item.get("value")
            if isinstance(value, int):
                return value
            if isinstance(value, str) and value.isdigit():
                return int(value)
    return 0


def main():
    games = (
        supabase.table("games")
        .select("id, home_team_name, away_team_name, raw_json")
        .eq("sport_key", "soccer")
        .in_("league_key", ["1", "479"])
        .limit(100)
        .execute()
        .data
    )

    saved = 0

    for game in games:
        raw = game.get("raw_json") or {}
        enriched = raw.get("enriched_details") or {}
        stats_response = enriched.get("statistics", {}).get("response", [])

        total_corners = 0

        for team_stats in stats_response:
            stats = team_stats.get("statistics", [])
            total_corners += get_stat_value(stats, "Corner Kicks")

        expected_corners = max(8.0, total_corners)

        over75 = 65 if expected_corners >= 8 else 48
        over85 = 58 if expected_corners >= 9 else 42
        over95 = 52 if expected_corners >= 10 else 35

        if over75 >= 60:
            pick = "Over 7.5 Corners"
            conf = over75
        else:
            pick = "Pass"
            conf = over75

        row = {
            "game_id": game["id"],
            "home_team_name": game["home_team_name"],
            "away_team_name": game["away_team_name"],
            "expected_corners": expected_corners,
            "over_75_probability": over75,
            "over_85_probability": over85,
            "over_95_probability": over95,
            "corners_pick": pick,
            "confidence": conf,
        }

        supabase.table("soccer_corners_predictions").insert(row).execute()
        saved += 1

    print(f"✅ Corners predictions created: {saved}")


if __name__ == "__main__":
    main()
    