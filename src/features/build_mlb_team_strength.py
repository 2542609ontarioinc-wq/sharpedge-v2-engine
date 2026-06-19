"""
Compute MLB team run-scoring and run-allowing strength vs league average.
Uses shrinkage toward 1.0 (SHRINK_K=5) so teams with fewer games pull toward
the league mean.  Writes to mlb_team_run_strength (upsert on team_name).

Only uses finished games (status='FT') from the current season.
"""
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"
SHRINK_K = 5
FALLBACK_LEAGUE_AVG = 4.5   # MLB historical average runs per team per game
CURRENT_SEASON = str(datetime.now(ZoneInfo("America/Toronto")).year)
FINISHED_STATUSES = {"FT", "AOT", "POST", "F", "Final", "Game Finished"}


def _safe(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def main():
    games = (
        supabase.table("games")
        .select("*")
        .eq("sport_key", SPORT_KEY)
        .eq("season", CURRENT_SEASON)
        .execute()
        .data
    )

    finished = [g for g in games if (g.get("status") or "").upper() in
                {s.upper() for s in FINISHED_STATUSES} or g.get("period", "").lower() in
                {"game finished", "final"}]

    if not finished:
        print("No finished MLB games found — skipping team strength build.")
        return

    # Collect runs scored/allowed per team
    scored = defaultdict(list)
    allowed = defaultdict(list)

    for g in finished:
        home = g.get("home_team_name")
        away = g.get("away_team_name")
        hs = _safe(g.get("home_score"))
        as_ = _safe(g.get("away_score"))
        if home:
            scored[home].append(hs)
            allowed[home].append(as_)
        if away:
            scored[away].append(as_)
            allowed[away].append(hs)

    # League average runs per team per game across all finished games
    all_runs = [r for rs in scored.values() for r in rs]
    league_avg = (sum(all_runs) / len(all_runs)) if all_runs else FALLBACK_LEAGUE_AVG
    if league_avg <= 0:
        league_avg = FALLBACK_LEAGUE_AVG

    saved = 0
    for team in set(list(scored.keys()) + list(allowed.keys())):
        s_list = scored.get(team, [])
        a_list = allowed.get(team, [])
        n = len(s_list)

        avg_scored = (sum(s_list) / n) if s_list else league_avg
        avg_allowed = (sum(a_list) / len(a_list)) if a_list else league_avg

        raw_scoring_idx = avg_scored / league_avg if league_avg else 1.0
        raw_allowed_idx = avg_allowed / league_avg if league_avg else 1.0

        # Shrink toward 1.0 (league average)
        w = n / (n + SHRINK_K)
        shrunk_scoring = round(max(0.4, min(2.5, w * raw_scoring_idx + (1 - w) * 1.0)), 4)
        shrunk_allowed = round(max(0.4, min(2.5, w * raw_allowed_idx + (1 - w) * 1.0)), 4)

        row = {
            "team_name": team,
            "season": CURRENT_SEASON,
            "games_played": n,
            "avg_runs_scored": round(avg_scored, 3),
            "avg_runs_allowed": round(avg_allowed, 3),
            "league_avg_runs": round(league_avg, 3),
            "run_scoring_index": round(raw_scoring_idx, 4),
            "run_allowed_index": round(raw_allowed_idx, 4),
            "shrunk_scoring_index": shrunk_scoring,
            "shrunk_allowed_index": shrunk_allowed,
            "updated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        }
        supabase.table("mlb_team_run_strength").upsert(row, on_conflict="team_name").execute()
        saved += 1

    print(f"✅ MLB team run strength computed: {saved} teams | league avg {league_avg:.2f} runs/team/game")


if __name__ == "__main__":
    main()
