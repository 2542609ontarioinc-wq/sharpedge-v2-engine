"""
Grade settled MLB player prop picks against actual game stats.

For each row in mlb_player_props where the linked game is finished:
  1. Fetch the player's game log for the season from MLB Stats API.
  2. Find the entry matching the game_date.
  3. Extract the relevant stat and compare vs market_line + pick_side.
  4. Upsert WIN / LOSS / VOID + units_result into mlb_prop_grades.

Stat extraction by prop_market:
  strikeouts      → strikeOuts
  outs_recorded   → inningsPitched (parsed to outs)
  earned_runs     → earnedRuns
  hits_allowed    → hits   (pitching group)
  walks           → baseOnBalls
  h_r_rbi         → hits + runs + rbi (hitting group)

Honesty rule: WIN with no odds = 0.0 units (break-even); LOSS = -1.0; VOID = 0.0.
"""
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"
FINISHED_STATUSES = {"ft", "aot", "f", "final", "game finished", "finished"}
# "post" = API-Sports status for Postponed — never treat as finished.
POSTPONED_STATUSES = {"postponed", "cancelled", "canceled", "suspended", "post"}


def _parse_ip(s):
    try:
        s = str(s or "").strip()
        if not s:
            return None
        if "." in s:
            whole, frac = s.split(".", 1)
            return int(whole) + int(frac[0]) / 3.0
        return float(s)
    except (ValueError, TypeError):
        return None


def _fetch_gamelog(player_mlb_id, season, group):
    """Return per-game stat splits for the player."""
    try:
        r = requests.get(
            f"{MLB_API_BASE}/people/{player_mlb_id}/stats",
            params={"stats": "gameLog", "season": season, "group": group},
            timeout=15,
        )
        r.raise_for_status()
        splits = []
        for grp in r.json().get("stats", []):
            splits.extend(grp.get("splits", []))
        return splits
    except Exception:
        return []


def _find_player_in_splits(splits, search_name: str):
    """
    Fuzzy player name lookup within a splits list (fallback utility).
    Tries: (a) exact lowercased match, (b) partial containment, (c) last-name match.
    Returns the first matching split, or None.  Used when player_mlb_id lookup fails.
    """
    if not search_name:
        return None
    needle = search_name.lower().strip()
    last = needle.split()[-1] if needle.split() else needle

    exact = partial = last_match = None
    for sp in splits:
        player = (sp.get("player") or {})
        full = (player.get("fullName") or "").lower().strip()
        if not full:
            continue
        if full == needle and exact is None:
            exact = sp
        if needle in full and partial is None:
            partial = sp
        if full.split()[-1] == last and last_match is None:
            last_match = sp

    return exact or partial or last_match


def _extract_split(splits, game_date_str, prop_market):
    """
    Find the split for game_date_str and return (value, ip, ab).

    ip  — innings pitched as a decimal float (e.g. 6.333 for 6⅓ IP), or None
    ab  — at-bats integer (0 means batter was scratched / didn't bat)
    value — the prop stat, or None if the date isn't found
    All three are None when no matching split exists.
    """
    for split in splits:
        if split.get("date") == game_date_str:
            s = split.get("stat") or {}
            ip = _parse_ip(s.get("inningsPitched"))
            ab = int(s.get("atBats") or 0)

            if prop_market == "strikeouts":
                value = float(s.get("strikeOuts") or 0)
            elif prop_market == "outs_recorded":
                value = round(ip * 3, 1) if ip is not None else None
            elif prop_market == "earned_runs":
                value = float(s.get("earnedRuns") or 0)
            elif prop_market == "hits_allowed":
                value = float(s.get("hits") or 0)
            elif prop_market == "walks":
                value = float(s.get("baseOnBalls") or 0)
            elif prop_market == "h_r_rbi":
                value = (
                    float(s.get("hits") or 0)
                    + float(s.get("runs") or 0)
                    + float(s.get("rbi") or 0)
                )
            else:
                value = None
            return value, ip, ab
    return None, None, None


def _grade(actual, line, pick_side):
    if actual is None:
        return "VOID"
    f_line = float(line)
    if pick_side.lower() == "over":
        return "WIN" if actual > f_line else "LOSS"
    else:
        if actual == f_line:
            return "VOID"
        return "WIN" if actual < f_line else "LOSS"


def _units(grade, odds_decimal):
    if grade == "VOID":
        return 0.0
    if grade == "LOSS":
        return -1.0
    if odds_decimal and float(odds_decimal) > 1.0:
        return round(float(odds_decimal) - 1.0, 2)
    return 0.0


def main():
    toronto = ZoneInfo("America/Toronto")
    season = datetime.now(toronto).year

    games = (
        supabase.table("games")
        .select("id,game_date,status,period")
        .eq("sport_key", SPORT_KEY)
        .execute()
        .data
    )
    # Only grade against games that are definitively Final in our DB.
    finished = {
        g["id"]: g for g in games
        if ((g.get("status") or "").lower() not in POSTPONED_STATUSES
            and (g.get("period") or "").lower() not in POSTPONED_STATUSES)
        and ((g.get("status") or "").lower() in FINISHED_STATUSES
             or (g.get("period") or "").lower() in FINISHED_STATUSES)
    }

    props = supabase.table("mlb_player_props").select("*").execute().data

    now = datetime.now(timezone.utc).isoformat()
    gamelog_cache = {}
    graded = 0

    for prop in props:
        gid = prop.get("game_id")
        if gid not in finished:
            continue

        game_date = finished[gid].get("game_date")
        if not game_date:
            continue

        player_id = prop.get("player_mlb_id")
        prop_market = prop.get("prop_market")
        market_line = prop.get("market_line")
        pick_side = prop.get("pick_side")

        if not all([player_id, prop_market, market_line is not None, pick_side]):
            continue

        cache_key = (player_id, prop.get("player_type"))
        if cache_key not in gamelog_cache:
            group = "pitching" if prop.get("player_type") == "pitcher" else "hitting"
            gamelog_cache[cache_key] = _fetch_gamelog(player_id, season, group)
            time.sleep(0.08)

        actual, ip, ab = _extract_split(gamelog_cache[cache_key], game_date, prop_market)

        # Void conditions — mirrors sportsbook rules:
        #   Pitcher props: VOID if no gamelog entry, 0 IP, or fewer than 3.0 IP
        #     (books void when the starter is pulled before completing 3 innings).
        #   Batter props: VOID if no gamelog entry or 0 at-bats (scratched / DNP).
        is_pitcher = prop.get("player_type") == "pitcher"
        if actual is None:
            grade = "VOID"
        elif is_pitcher and (ip is None or ip < 3.0):
            grade = "VOID"
        elif not is_pitcher and ab == 0:
            grade = "VOID"
        else:
            grade = _grade(actual, market_line, pick_side)

        units = _units(grade, prop.get("best_odds_decimal"))

        row = {
            "game_id": gid,
            "game_date": game_date,
            "player_name": prop.get("player_name"),
            "player_mlb_id": player_id,
            "player_type": prop.get("player_type"),
            "prop_market": prop_market,
            "market_line": market_line,
            "pick_side": pick_side,
            "actual_value": actual,
            "grade": grade,
            "edge_flag": prop.get("edge_flag"),
            "best_odds_decimal": prop.get("best_odds_decimal"),
            "units_result": units,
            "graded_at": now,
        }
        supabase.table("mlb_prop_grades").upsert(
            row, on_conflict="game_id,player_mlb_id,prop_market"
        ).execute()

        actual_str = f"{actual:.1f}" if actual is not None else "?"
        print(
            f"  {prop.get('player_name')} {prop_market} "
            f"{pick_side} {market_line}: actual={actual_str} → {grade} ({units:+.2f}u)"
        )
        graded += 1

    print(f"\n✅ MLB prop grades: {graded}")


if __name__ == "__main__":
    main()
