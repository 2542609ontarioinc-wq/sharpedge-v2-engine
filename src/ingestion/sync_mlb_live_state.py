"""
Fetch live linescore data for MLB games that have active picks.

Writes to mlb_live_state (keyed by our internal game_id).
Display-only: never reads from or writes to mlb_pick_grades or mlb_prop_grades.

Uses the MLB Stats API schedule endpoint with linescore hydration — a single
bulk call per date, no API key required.
"""
from datetime import datetime, timedelta, timezone

import requests
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
SPORT_ID = 1


# ---------------------------------------------------------------------------
# Team-name normalisation — matches the pattern in grade_mlb_picks.py so
# any team that grades correctly also matches correctly in live state.
# ---------------------------------------------------------------------------

_NAME_OVERRIDES: dict[str, str] = {
    "oakland athletics": "athletics",
    "sacramento athletics": "athletics",
    "arizona diamondbacks": "diamondbacks",
    "washington nationals": "nationals",
    "san francisco giants": "giants",
    "chicago white sox": "white sox",
}


def _norm(name: str) -> str:
    n = (name or "").lower().strip()
    return _NAME_OVERRIDES.get(n, n)


def _teams_match(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if na == nb:
        return True
    # Fallback: compare last word (team nickname).
    return na.split()[-1] == nb.split()[-1] if na and nb else False


# ---------------------------------------------------------------------------
# MLB Stats API helpers
# ---------------------------------------------------------------------------

def _fetch_schedule(date_str: str) -> list[dict]:
    """Return raw game dicts from the MLB Stats API for a given date."""
    try:
        r = requests.get(
            MLB_SCHEDULE_URL,
            params={
                "sportId": SPORT_ID,
                "date": date_str,
                "hydrate": "linescore,probablePitcher",
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        print(f"  [live-state] MLB Stats API error for {date_str}: {exc}")
        return []

    games = []
    for date_block in data.get("dates", []):
        games.extend(date_block.get("games", []))
    return games


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # 1. Find all game_ids that have picks (sharp or safe-zone).
    pred_rows = supabase.table("mlb_final_predictions").select("game_id").execute().data
    sz_rows = supabase.table("mlb_safe_zone").select("game_id").execute().data
    pick_game_ids = {r["game_id"] for r in (pred_rows or []) + (sz_rows or []) if r.get("game_id")}

    if not pick_game_ids:
        print("  [live-state] No pick game_ids found — nothing to track.")
        return

    # 2. Fetch those games from our games table (team names + dates).
    games_data = (
        supabase.table("games")
        .select("id,game_date,home_team_name,away_team_name")
        .in_("id", list(pick_game_ids))
        .execute()
        .data
    ) or []

    if not games_data:
        print("  [live-state] No matching rows in games table.")
        return

    # 3. Build a lookup: (game_date, home_norm, away_norm) → game_id
    lookup: dict[tuple[str, str, str], str] = {}
    dates_needed: set[str] = set()
    for g in games_data:
        date = g.get("game_date") or ""
        home = _norm(g.get("home_team_name") or "")
        away = _norm(g.get("away_team_name") or "")
        if date and home and away:
            lookup[(date, home, away)] = g["id"]
            dates_needed.add(date)

    # Also check yesterday in case late games ran past midnight UTC.
    today = datetime.now(timezone.utc)
    yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    dates_needed.add(today.strftime("%Y-%m-%d"))
    dates_needed.add(yesterday)

    # 4. Fetch MLB Stats API schedule for each relevant date.
    mlb_games: list[dict] = []
    for date_str in sorted(dates_needed):
        fetched = _fetch_schedule(date_str)
        mlb_games.extend(fetched)
        print(f"  [live-state] {date_str}: {len(fetched)} games from MLB Stats API")

    if not mlb_games:
        print("  [live-state] No games returned from MLB Stats API.")
        return

    # 5. Match MLB Stats API games to our internal game_ids and upsert.
    now = datetime.now(timezone.utc).isoformat()
    upserted = 0
    unmatched = 0

    for g in mlb_games:
        status_obj = g.get("status", {})
        detail = status_obj.get("detailedState") or status_obj.get("abstractGameState") or ""

        teams = g.get("teams", {})
        home_team = (teams.get("home", {}).get("team", {}).get("name") or "")
        away_team = (teams.get("away", {}).get("team", {}).get("name") or "")

        # Game date from MLB Stats API (format: "YYYY-MM-DD" in officialDate).
        mlb_date = g.get("officialDate") or g.get("gameDate", "")[:10]

        # Try exact match first, then fuzzy per-date window.
        game_id: str | None = None
        for (stored_date, stored_home, stored_away), gid in lookup.items():
            if stored_date != mlb_date:
                continue
            if _teams_match(home_team, stored_home) and _teams_match(away_team, stored_away):
                game_id = gid
                break

        if not game_id:
            unmatched += 1
            continue

        # Extract linescore.
        ls = g.get("linescore") or {}
        ls_teams = ls.get("teams") or {}
        home_ls = ls_teams.get("home") or {}
        away_ls = ls_teams.get("away") or {}

        home_score = home_ls.get("runs")
        away_score = away_ls.get("runs")
        inning = ls.get("currentInning")
        inning_half = ls.get("inningHalf")
        outs = ls.get("outs")

        # Probable pitchers (scheduled starters).
        home_pitcher_obj = teams.get("home", {}).get("probablePitcher") or {}
        away_pitcher_obj = teams.get("away", {}).get("probablePitcher") or {}
        home_pitcher = home_pitcher_obj.get("fullName")
        away_pitcher = away_pitcher_obj.get("fullName")

        row = {
            "game_id": game_id,
            "home_score": int(home_score) if home_score is not None else None,
            "away_score": int(away_score) if away_score is not None else None,
            "inning": int(inning) if inning is not None else None,
            "inning_half": inning_half,
            "outs": int(outs) if outs is not None else None,
            "game_status": detail,
            "home_pitcher": home_pitcher,
            "away_pitcher": away_pitcher,
            "captured_at": now,
        }
        supabase.table("mlb_live_state").upsert(row, on_conflict="game_id").execute()
        upserted += 1

    print(
        f"  [live-state] ✅ {upserted} game(s) upserted to mlb_live_state "
        f"({unmatched} unmatched from MLB Stats API)"
    )


if __name__ == "__main__":
    main()
