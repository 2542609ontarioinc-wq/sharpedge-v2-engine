from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MIN_STAT_ROWS = 3  # both teams need at least this many history rows to model


def get_priority_league_keys():
    rows = supabase.table("priority_leagues").select("league_id").execute().data
    return [str(r["league_id"]) for r in rows]


def stat_row_count(team_name):
    result = (
        supabase.table("soccer_team_stat_history")
        .select("id", count="exact")
        .eq("team_name", team_name)
        .execute()
    )
    return result.count or 0


def get_latest_form(game_id, team_name):
    rows = (
        supabase.table("soccer_form_features")
        .select("*")
        .eq("game_id", game_id)
        .eq("team_name", team_name)
        .gt("matches_checked", 0)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
        .data
    )
    return rows[0]["form_score"] if rows else 50


def save_strength(game):
    home_score = get_latest_form(game["id"], game["home_team_name"])
    away_score = get_latest_form(game["id"], game["away_team_name"])
    diff = round(home_score - away_score, 2)
    if diff >= 20:
        edge = "home_strong_edge"
    elif diff <= -20:
        edge = "away_strong_edge"
    elif diff >= 8:
        edge = "home_small_edge"
    elif diff <= -8:
        edge = "away_small_edge"
    else:
        edge = "balanced"
    row = {
        "game_id": game["id"],
        "home_team_name": game["home_team_name"],
        "away_team_name": game["away_team_name"],
        "home_form_score": home_score,
        "away_form_score": away_score,
        "form_difference": diff,
        "predicted_edge": edge,
    }
    # Delete before insert makes each run idempotent without needing a unique
    # constraint. sql/091 adds that constraint to allow upsert once applied.
    supabase.table("soccer_match_strength").delete().eq("game_id", game["id"]).execute()
    supabase.table("soccer_match_strength").insert(row).execute()


def main():
    # Pass 1: games in priority leagues (reads from DB, not a stale hardcoded list).
    priority_keys = get_priority_league_keys()
    today = datetime.now(ZoneInfo("America/Toronto")).date()
    week_out = today + timedelta(days=7)

    priority_games = (
        supabase.table("games")
        .select("id, home_team_name, away_team_name, league_key")
        .eq("sport_key", "soccer")
        .in_("league_key", priority_keys)
        .gte("game_date", str(today))
        .lte("game_date", str(week_out))
        .execute()
        .data
    )
    priority_ids = {g["id"] for g in priority_games}
    print(f"  Priority-league games this week: {len(priority_games)}")

    # Pass 2: games with Odds API coverage outside priority leagues, but only
    # if both teams have enough historical data (MIN_STAT_ROWS). This opens the
    # model to any odds-covered game without fabricating picks for data-free teams.
    odds_covered = (
        supabase.table("soccer_odds")
        .select("game_id")
        .not_.is_("game_id", "null")
        .execute()
        .data
    )
    covered_ids = {r["game_id"] for r in odds_covered if r.get("game_id")}
    extra_ids = covered_ids - priority_ids

    extra_games = []
    if extra_ids:
        extra_rows = (
            supabase.table("games")
            .select("id, home_team_name, away_team_name, league_key")
            .eq("sport_key", "soccer")
            .in_("id", list(extra_ids))
            .gte("game_date", str(today))
            .lte("game_date", str(week_out))
            .execute()
            .data
        )
        for g in extra_rows:
            h_count = stat_row_count(g["home_team_name"])
            a_count = stat_row_count(g["away_team_name"])
            if h_count >= MIN_STAT_ROWS and a_count >= MIN_STAT_ROWS:
                extra_games.append(g)
            else:
                print(f"  Skipping {g['home_team_name']} vs {g['away_team_name']} "
                      f"— stat rows: {h_count}/{a_count} (need {MIN_STAT_ROWS})")

    all_games = priority_games + extra_games
    saved = 0
    for game in all_games:
        save_strength(game)
        saved += 1

    print(f"✅ Match strength rows saved: {saved} "
          f"({len(priority_games)} priority, {len(extra_games)} odds-expanded)")


if __name__ == "__main__":
    main()
