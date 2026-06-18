"""
Poisson run model for MLB.

For each upcoming game, reads shrunk team run-strength indices and produces:
  - Moneyline win probabilities (home/away)
  - Totals: Over/Under 7.5, 8.5, 9.5
  - Run-line: home/away -1.5, +1.5, +2.5

No Dixon-Coles correction (that corrects Poisson for low-score football goals;
MLB run totals are large enough that independence holds reasonably).

Results written to mlb_run_predictions (upsert on game_id, model_version).
"""
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MAX_RUNS = 25
HOME_ADV = 1.04          # small home-field advantage in MLB
FALLBACK_LEAGUE_AVG = 4.5
MODEL_VERSION = "poisson_v2"
SPORT_KEY = "baseball_mlb"
PITCHER_WEIGHT = 0.6     # blend: 60% starting pitcher RA9 / 40% team defense


def _safe(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def build_run_matrix(home_xr, away_xr):
    """Return probability matrix P[i][j] = P(home scores i, away scores j)."""
    matrix = [[0.0] * (MAX_RUNS + 1) for _ in range(MAX_RUNS + 1)]
    total = 0.0
    for i in range(MAX_RUNS + 1):
        phi = poisson_pmf(i, home_xr)
        for j in range(MAX_RUNS + 1):
            p = phi * poisson_pmf(j, away_xr)
            matrix[i][j] = p
            total += p
    if total > 0:
        for i in range(MAX_RUNS + 1):
            for j in range(MAX_RUNS + 1):
                matrix[i][j] /= total
    return matrix


def markets_from_matrix(matrix, home_xr, away_xr):
    home_win = away_win = 0.0
    over_75 = over_85 = over_95 = 0.0
    home_rl_m15 = home_rl_p15 = home_rl_p25 = 0.0

    for i in range(MAX_RUNS + 1):
        for j in range(MAX_RUNS + 1):
            p = matrix[i][j]
            if p <= 0:
                continue
            diff = i - j
            total = i + j

            if i > j:
                home_win += p
            elif i < j:
                away_win += p

            if total > 7.5:
                over_75 += p
            if total > 8.5:
                over_85 += p
            if total > 9.5:
                over_95 += p

            # run line (home perspective)
            if diff >= 2:
                home_rl_m15 += p   # home -1.5 covers (wins by 2+)
            if diff >= -1:
                home_rl_p15 += p   # home +1.5 covers (wins or loses by 1)
            if diff >= -2:
                home_rl_p25 += p   # home +2.5 covers (wins or loses by <=2)

    def pct(v):
        return round(v * 100, 2)

    return {
        "home_win_probability":   pct(home_win),
        "away_win_probability":   pct(away_win),
        "over_75_probability":    pct(over_75),
        "over_85_probability":    pct(over_85),
        "over_95_probability":    pct(over_95),
        "under_75_probability":   pct(1 - over_75),
        "under_85_probability":   pct(1 - over_85),
        "under_95_probability":   pct(1 - over_95),
        "home_rl_minus15_prob":   pct(home_rl_m15),
        "home_rl_plus15_prob":    pct(home_rl_p15),
        "home_rl_plus25_prob":    pct(home_rl_p25),
        "away_rl_minus15_prob":   pct(1 - home_rl_p15),   # away wins by 2+
        "away_rl_plus15_prob":    pct(1 - home_rl_m15),   # away +1.5 covers
        "away_rl_plus25_prob":    pct(1 - (1 - home_rl_p25)),   # = home_rl_p25 mirrored
    }


def build_strengths():
    rows = supabase.table("mlb_team_run_strength").select("*").execute().data
    return {r["team_name"]: r for r in rows}


def build_pitcher_adjustments():
    """Load today's probable starters keyed by (game_id, side)."""
    rows = (
        supabase.table("mlb_pitchers")
        .select("game_id,side,pitcher_name,shrunk_ra9_index,games_started")
        .execute()
        .data
    )
    return {(r["game_id"], r["side"]): r for r in rows}


def main():
    toronto = ZoneInfo("America/Toronto")
    today = datetime.now(toronto).date()
    window_end = (today + timedelta(days=3)).isoformat()

    games = (
        supabase.table("games")
        .select("*")
        .eq("sport_key", SPORT_KEY)
        .gte("game_date", today.isoformat())
        .lte("game_date", window_end)
        .execute()
        .data
    )

    if not games:
        print("No upcoming MLB games found.")
        return

    strengths = build_strengths()
    league_avgs = [r["league_avg_runs"] for r in strengths.values() if r.get("league_avg_runs")]
    league_avg = (sum(league_avgs) / len(league_avgs)) if league_avgs else FALLBACK_LEAGUE_AVG

    pitchers = build_pitcher_adjustments()

    seen = set()
    saved = 0

    for g in games:
        gid = g["id"]
        if gid in seen:
            continue
        seen.add(gid)

        home = g["home_team_name"]
        away = g["away_team_name"]

        hs = strengths.get(home)
        as_ = strengths.get(away)

        h_score = _safe(hs["shrunk_scoring_index"] if hs else None, 1.0)
        h_allow = _safe(hs["shrunk_allowed_index"] if hs else None, 1.0)
        a_score = _safe(as_["shrunk_scoring_index"] if as_ else None, 1.0)
        a_allow = _safe(as_["shrunk_allowed_index"] if as_ else None, 1.0)

        home_pitcher = pitchers.get((gid, "home"))
        away_pitcher = pitchers.get((gid, "away"))

        home_p_idx = _safe(home_pitcher["shrunk_ra9_index"] if home_pitcher else None, None)
        away_p_idx = _safe(away_pitcher["shrunk_ra9_index"] if away_pitcher else None, None)

        # Away pitcher faces home offense → blends into home team's expected runs
        # Home pitcher faces away offense → blends into away team's expected runs
        a_def = (PITCHER_WEIGHT * away_p_idx + (1 - PITCHER_WEIGHT) * a_allow) if away_p_idx is not None else a_allow
        h_def = (PITCHER_WEIGHT * home_p_idx + (1 - PITCHER_WEIGHT) * h_allow) if home_p_idx is not None else h_allow

        home_xr = max(0.5, min(15.0, league_avg * h_score * a_def * HOME_ADV))
        away_xr = max(0.5, min(15.0, league_avg * a_score * h_def))

        matrix = build_run_matrix(home_xr, away_xr)
        m = markets_from_matrix(matrix, home_xr, away_xr)

        row = {
            "game_id": gid,
            "model_version": MODEL_VERSION,
            "home_team_name": home,
            "away_team_name": away,
            "expected_home_runs": round(home_xr, 3),
            "expected_away_runs": round(away_xr, 3),
            "expected_total_runs": round(home_xr + away_xr, 3),
            **m,
        }
        supabase.table("mlb_run_predictions").upsert(
            row, on_conflict="game_id,model_version"
        ).execute()
        saved += 1

        h_data = "strength" if hs else "prior"
        a_data = "strength" if as_ else "prior"
        hp_label = f"{home_pitcher['pitcher_name']} idx={home_pitcher['shrunk_ra9_index']}" if home_pitcher else "TBD"
        ap_label = f"{away_pitcher['pitcher_name']} idx={away_pitcher['shrunk_ra9_index']}" if away_pitcher else "TBD"
        print(
            f"{home} vs {away} | xR {home_xr:.2f}-{away_xr:.2f} | "
            f"ML {m['home_win_probability']}/{m['away_win_probability']} | "
            f"O8.5 {m['over_85_probability']} | RL h-1.5 {m['home_rl_minus15_prob']} "
            f"[{h_data}/{a_data}]\n"
            f"  SP: {home}→{hp_label} | {away}→{ap_label}"
        )

    print(f"\n✅ MLB Poisson run predictions saved: {saved}")


if __name__ == "__main__":
    main()
