import time
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from src.ingestion.apisports_client import APISportsClient

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
client = APISportsClient()


def stat_value(stats, name):
    for item in stats:
        if item.get("type") == name:
            v = item.get("value")
            if v is None:
                return 0
            if isinstance(v, int):
                return v
            if isinstance(v, str):
                c = v.replace("%", "").strip()
                if c.isdigit():
                    return int(c)
    return 0


def collect_team_ids():
    # Only teams that appear in PRIORITY-league games (the ones we publish
    # picks on). Prevents pulling thousands of irrelevant teams.
    pri = (
        supabase.table("priority_leagues")
        .select("league_id")
        .eq("sport_key", "soccer")
        .eq("enabled", True)
        .execute()
        .data
    )
    priority_ids = {str(r["league_id"]) for r in pri}

    games = (
        supabase.table("games")
        .select("league_key, raw_json")
        .eq("sport_key", "soccer")
        .limit(5000)
        .execute()
        .data
    )
    ids = {}
    for g in games:
        if str(g.get("league_key")) not in priority_ids:
            continue
        teams = (g.get("raw_json") or {}).get("teams") or {}
        for side in ("home", "away"):
            t = teams.get(side) or {}
            if t.get("id"):
                ids[t["id"]] = t.get("name")
    return ids


def fixture_stats(fixture_id):
    try:
        data = client.get_soccer_fixture_statistics(fixture_id)
        return data.get("response", [])
    except Exception:
        return []


def main():
    team_ids = collect_team_ids()
    print(f"Unique teams to sync: {len(team_ids)}")

    saved = 0
    calls = 0

    for team_id, team_name in team_ids.items():
        try:
            data = client._get(
                f"{client.football_base_url}/fixtures",
                params={"team": team_id, "last": 10},
            )
            calls += 1
        except Exception as e:
            print("skip", team_name, str(e)[:50])
            continue

        fixtures = data.get("response", [])

        for item in fixtures:
            fx = item.get("fixture", {})
            lg = item.get("league", {})
            teams = item.get("teams", {})
            goals = item.get("goals", {})

            status = (fx.get("status") or {}).get("short")
            if status not in ("FT", "AET", "PEN"):
                continue

            home = teams.get("home", {})
            away = teams.get("away", {})
            is_home = home.get("id") == team_id

            gf = goals.get("home") if is_home else goals.get("away")
            ga = goals.get("away") if is_home else goals.get("home")
            if gf is None or ga is None:
                continue

            opp = away if is_home else home
            fixture_id = str(fx.get("id"))

            stats_resp = fixture_stats(fx.get("id"))
            calls += 1
            my_stats = []
            for ts in stats_resp:
                if (ts.get("team") or {}).get("id") == team_id:
                    my_stats = ts.get("statistics", [])
                    break

            row = {
                "fixture_id": fixture_id,
                "league_id": str(lg.get("id")),
                "league_name": lg.get("name"),
                "season": str(lg.get("season")),
                "game_date": (fx.get("date") or "")[:10],
                "team_id": str(team_id),
                "team_name": team_name,
                "opponent_team_id": str(opp.get("id")),
                "opponent_team_name": opp.get("name"),
                "is_home": is_home,
                "goals_for": gf,
                "goals_against": ga,
                "shots_total": stat_value(my_stats, "Total Shots"),
                "shots_on_goal": stat_value(my_stats, "Shots on Goal"),
                "possession_percent": stat_value(my_stats, "Ball Possession"),
                "corners": stat_value(my_stats, "Corner Kicks"),
                "fouls": stat_value(my_stats, "Fouls"),
                "yellow_cards": stat_value(my_stats, "Yellow Cards"),
                "red_cards": stat_value(my_stats, "Red Cards"),
                "raw_json": item,
            }

            supabase.table("soccer_team_stat_history").upsert(
                row, on_conflict="fixture_id,team_id"
            ).execute()
            saved += 1

        print(f"{team_name}: synced ({saved} rows so far, {calls} api calls)")
        time.sleep(0.3)

    print(f"\n✅ Deep team history rows upserted: {saved} | API calls used: {calls}")


if __name__ == "__main__":
    main()
