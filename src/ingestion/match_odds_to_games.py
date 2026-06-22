from difflib import SequenceMatcher
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def similarity(a, b):
    if not a or not b:
        return 0

    return SequenceMatcher(
        None,
        a.lower().strip(),
        b.lower().strip(),
    ).ratio()


def match_score(odds_home, odds_away, game_home, game_away):
    return (
        similarity(odds_home, game_home)
        + similarity(odds_away, game_away)
    ) / 2


def main():
    # Only process odds captured in the last 24 hours — stale unmatched rows
    # from prior runs are already lost causes and should not bury fresh ones.
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    odds_games = (
        supabase.table("soccer_odds")
        .select("home_team_name, away_team_name")
        .is_("game_id", "null")
        .gte("captured_at", cutoff)
        .limit(500)
        .execute()
        .data
    )

    unique_odds_games = []
    seen = set()

    for row in odds_games:
        key = (row["home_team_name"], row["away_team_name"])
        if key not in seen:
            seen.add(key)
            unique_odds_games.append(row)

    # Only consider upcoming games so we stay well under any row limit even
    # as the historical table grows. The 7-day window comfortably covers all
    # odds the API will return for upcoming matches.
    today = datetime.now(ZoneInfo("America/Toronto")).date()
    week_out = today + timedelta(days=7)
    games = (
        supabase.table("games")
        .select("id, home_team_name, away_team_name")
        .eq("sport_key", "soccer")
        .gte("game_date", str(today))
        .lte("game_date", str(week_out))
        .execute()
        .data
    )

    matched = 0

    for odds_game in unique_odds_games:
        best_game = None
        best_score = 0

        for game in games:
            score = match_score(
                odds_game["home_team_name"],
                odds_game["away_team_name"],
                game["home_team_name"],
                game["away_team_name"],
            )

            if score > best_score:
                best_score = score
                best_game = game

        if best_game and best_score >= 0.75:
            supabase.table("soccer_odds").update(
                {"game_id": best_game["id"]}
            ).eq(
                "home_team_name",
                odds_game["home_team_name"],
            ).eq(
                "away_team_name",
                odds_game["away_team_name"],
            ).execute()

            print(
                "Matched:",
                odds_game["home_team_name"],
                "vs",
                odds_game["away_team_name"],
                "=>",
                best_game["home_team_name"],
                "vs",
                best_game["away_team_name"],
                "| score:",
                round(best_score, 2),
            )

            matched += 1

    print(f"✅ Odds games matched: {matched}")


if __name__ == "__main__":
    main()
    