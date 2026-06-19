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
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MAX_RUNS = 25
HOME_ADV = 1.04          # small home-field advantage in MLB
FALLBACK_LEAGUE_AVG = 4.5
MODEL_VERSION = "poisson_v2"
MODEL_VERSION_BP = "poisson_v3_bullpen"
MODEL_VERSION_LU = "poisson_v4_lineup"
MODEL_VERSION_ENV = "poisson_v5_environment"
SPORT_KEY = "baseball_mlb"
PITCHER_WEIGHT = 0.6     # blend: 60% starting pitcher RA9 / 40% team defense
DEFAULT_STARTER_IP = 5.5  # historical MLB average IP/GS when starter data is missing


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
        .select("game_id,side,pitcher_name,shrunk_ra9_index,games_started,innings_pitched")
        .execute()
        .data
    )
    return {(r["game_id"], r["side"]): r for r in rows}


def build_lineup_data(today):
    """
    Load today's batter split stats and pitcher handedness for the v4 lineup model.

    Returns:
      batter_splits  — dict (player_mlb_id, split) → shrunk_ops_index
      game_lineups   — dict (game_id, side)        → list of player rows
      pitcher_hands  — dict (game_id, side)        → 'L' | 'R' | None
    """
    # Batter splits (may be empty if sync_mlb_batter_stats hasn't run yet)
    try:
        brows = (
            supabase.table("mlb_batter_strength")
            .select("player_mlb_id,split,shrunk_ops_index")
            .eq("game_date", today.isoformat())
            .execute()
            .data
        )
        batter_splits = {
            (r["player_mlb_id"], r["split"]): float(r["shrunk_ops_index"])
            for r in brows
            if r.get("shrunk_ops_index") is not None
        }
    except Exception:
        batter_splits = {}

    # Confirmed lineups for today
    try:
        lrows = (
            supabase.table("mlb_lineups")
            .select("game_id,side,player_mlb_id,batting_order")
            .eq("game_date", today.isoformat())
            .execute()
            .data
        )
        game_lineups = {}
        for r in lrows:
            game_lineups.setdefault((r["game_id"], r["side"]), []).append(r)
    except Exception:
        game_lineups = {}

    # Pitcher handedness from mlb_pitchers (today + yesterday for double-headers)
    try:
        prows = (
            supabase.table("mlb_pitchers")
            .select("game_id,side,pitch_hand")
            .gte("game_date", today.isoformat())
            .execute()
            .data
        )
        pitcher_hands = {(r["game_id"], r["side"]): r.get("pitch_hand") for r in prows}
    except Exception:
        pitcher_hands = {}

    return batter_splits, game_lineups, pitcher_hands


def _lineup_offense_factor(game_id, batting_side, pitcher_side,
                            batter_splits, game_lineups, pitcher_hands):
    """
    Aggregate OPS index for `batting_side`'s confirmed lineup vs the opposing pitcher's
    handedness.  Returns float (≈1.0 = league average) or None (fall back to team avg).

    Requires: pitch_hand known, >= 5 batters with split data.
    """
    opp_hand = pitcher_hands.get((game_id, pitcher_side))
    if not opp_hand or opp_hand == "S":
        return None

    batters = game_lineups.get((game_id, batting_side), [])
    if not batters:
        return None

    split_key = "vL" if opp_hand == "L" else "vR"
    indices = []
    for b in batters:
        pid = b.get("player_mlb_id")
        if not pid:
            continue
        idx = batter_splits.get((pid, split_key))
        if idx is not None:
            indices.append(idx)

    if len(indices) < 5:
        return None  # too few batters confirmed; trust team average

    return sum(indices) / len(indices)


def compute_xr_v4(home_pitcher, away_pitcher, home_bp, away_bp,
                  h_score, a_score, h_allow, a_allow, league_avg,
                  home_off_factor=None, away_off_factor=None):
    """
    v4: v3 bullpen-aware defense + lineup-aware offense.

    When lineup offense factors are available they replace the team-level scoring
    indices (h_score / a_score) on the offense side only.  The defense side (starter
    + bullpen split) is identical to compute_xr_v3.  Falls back to team average on
    either side when lineup data is missing.
    """
    h_off = home_off_factor if home_off_factor is not None else h_score
    a_off = away_off_factor if away_off_factor is not None else a_score
    return compute_xr_v3(
        home_pitcher, away_pitcher, home_bp, away_bp,
        h_off, a_off, h_allow, a_allow, league_avg,
    )


# ---------------------------------------------------------------------------
# v5: Park factors + weather (Open-Meteo, free/keyless)
# ---------------------------------------------------------------------------

# Each entry: (keyword_in_team_name, park_run_adj, is_covered, lat, lon, cf_bearing_deg)
# park_run_adj  — expected-total-runs adjustment at this park vs neutral (runs/game)
# is_covered    — dome/retractable: skip weather fetch
# cf_bearing    — compass degrees from home plate toward center field (for wind direction)
_TEAM_STADIUM = [
    # keyword must be distinctive within MLB; ordered specific-first for substring matching
    ("white sox",  0.00, False, 41.8299,  -87.6338,  50),   # Guaranteed Rate Field
    ("red sox",    0.10, False, 42.3467,  -71.0972,  45),   # Fenway Park
    ("blue jays",  0.00, True,  43.6414,  -79.3894,   0),   # Rogers Centre (dome)
    ("diamondback",0.00, True,  33.4453, -112.0667,   0),   # Chase Field (retractable)
    ("braves",    -0.05, False, 33.8907,  -84.4677,  30),   # Truist Park
    ("orioles",    0.15, False, 39.2839,  -76.6222,  45),   # Camden Yards
    ("cubs",       0.05, False, 41.9484,  -87.6553,  25),   # Wrigley Field
    ("reds",       0.25, False, 39.0979,  -84.5082,  30),   # Great American Ball Park
    ("guardians", -0.05, False, 41.4962,  -81.6853, 330),   # Progressive Field
    ("rockies",    0.80, False, 39.7559, -104.9942, 310),   # Coors Field
    ("tigers",    -0.05, False, 42.3390,  -83.0485, 345),   # Comerica Park
    ("astros",     0.05, True,  29.7573,  -95.3555,   0),   # Minute Maid (retractable)
    ("royals",     0.00, False, 39.0517,  -94.4803,  25),   # Kauffman Stadium
    ("angels",     0.00, False, 33.8003, -117.8827, 250),   # Angel Stadium
    ("dodgers",   -0.05, False, 34.0739, -118.2400, 305),   # Dodger Stadium
    ("marlins",   -0.20, True,  25.7781,  -80.2195,   0),   # loanDepot Park (retractable)
    ("brewers",    0.10, True,  43.0280,  -87.9712,   0),   # American Family Field (retractable)
    ("twins",      0.00, False, 44.9817,  -93.2775, 325),   # Target Field
    ("mets",      -0.05, False, 40.7569,  -73.8459,  50),   # Citi Field
    ("yankees",    0.10, False, 40.8296,  -73.9262, 320),   # Yankee Stadium
    ("athletics",  0.00, False, 38.5789, -121.5080, 310),   # Sutter Health (temp) — neutral
    ("phillies",   0.15, False, 39.9061,  -75.1665,  25),   # Citizens Bank Park
    ("pirates",   -0.10, False, 40.4469,  -80.0057,  50),   # PNC Park
    ("padres",    -0.20, False, 32.7076, -117.1570, 310),   # Petco Park
    ("mariners",  -0.10, False, 47.5914, -122.3325,  25),   # T-Mobile Park
    ("giants",    -0.30, False, 37.7786, -122.3893, 315),   # Oracle Park
    ("cardinals", -0.05, False, 38.6226,  -90.1928,  25),   # Busch Stadium
    ("rays",      -0.05, True,  27.7683,  -82.6534,   0),   # Tropicana Field (dome)
    ("rangers",    0.15, True,  32.7473,  -97.0845,   0),   # Globe Life Field (retractable)
    ("nationals",  0.00, False, 38.8730,  -77.0074, 340),   # Nationals Park
]


def _team_to_stadium_info(team_name):
    """Return (park_run_adj, is_covered, lat, lon, cf_bearing) or neutral defaults."""
    tn = (team_name or "").lower()
    for kw, run_adj, covered, lat, lon, cf_bear in _TEAM_STADIUM:
        if kw in tn:
            return run_adj, covered, lat, lon, cf_bear
    return 0.0, True, None, None, 0   # unknown → no adjustment, skip weather


def _game_hour_utc(start_time_utc):
    """Extract UTC hour from start_time_utc string; default 23 (≈7 PM ET) if missing."""
    if not start_time_utc:
        return 23
    try:
        dt = datetime.fromisoformat(str(start_time_utc).replace("Z", "+00:00"))
        return dt.hour
    except Exception:
        return 23


def _fetch_weather_open_meteo(lat, lon, game_date_str, game_hour_utc, cache):
    """
    Fetch hourly weather from Open-Meteo (free, keyless) for the game-time hour.
    Returns (temp_c, windspeed_kmh, wind_dir_from_deg) or None on failure.
    Cache key is (lat, lon, game_date_str) to avoid duplicate calls per stadium/day.
    """
    cache_key = (round(lat, 4), round(lon, 4), game_date_str)
    if cache_key in cache:
        return cache[cache_key]
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,windspeed_10m,winddirection_10m",
                "forecast_days": 3,
                "timezone": "UTC",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            cache[cache_key] = None
            return None
        data = resp.json()
        times = data["hourly"]["time"]
        target = f"{game_date_str}T{game_hour_utc:02d}:00"
        idx = next((i for i, t in enumerate(times) if t >= target), len(times) - 1)
        result = (
            data["hourly"]["temperature_2m"][idx],
            data["hourly"]["windspeed_10m"][idx],
            data["hourly"]["winddirection_10m"][idx],
        )
    except Exception:
        result = None
    cache[cache_key] = result
    return result


def _angle_diff(a, b):
    """Smallest angle between two compass bearings (0–180°)."""
    return abs((a - b + 180) % 360 - 180)


def _weather_adj(temp_c, wind_kmh, wind_dir_from, cf_bearing):
    """
    Expected-total-runs adjustment for weather. Outdoor stadiums only.
    Returns signed float (positive = more runs expected).
    Adjustments are intentionally small: fractions of a run.
    """
    adj = 0.0

    # Temperature effect
    if temp_c is not None:
        if temp_c < 2:       # below 35 °F — ball doesn't carry, pitchers favored
            adj -= 0.25
        elif temp_c < 7:     # below 45 °F
            adj -= 0.12
        elif temp_c > 29:    # above 85 °F — ball carries, thin/warm air
            adj += 0.07

    # Wind effect: check if blowing out (toward CF) or in (from CF)
    if wind_kmh is not None and wind_kmh > 15:
        wind_toward = (wind_dir_from + 180) % 360   # meteorological → compass
        diff = _angle_diff(wind_toward, cf_bearing)
        if diff < 45:
            direction_factor = 1.0    # OUT — helps batters
        elif diff > 135:
            direction_factor = -1.0   # IN  — hurts batters
        else:
            direction_factor = 0.0    # crosswind — wash

        if wind_kmh > 40:
            magnitude = 0.18
        elif wind_kmh > 25:
            magnitude = 0.10
        else:
            magnitude = 0.05

        adj += direction_factor * magnitude

    return adj


def compute_xr_v5(home_xr_v4, away_xr_v4, env_adj_total):
    """
    v5 = v4 + environment. env_adj_total is the total run adjustment (park + weather)
    applied to the game total and split equally between home and away expected runs.
    """
    half = env_adj_total / 2.0
    return (
        max(0.5, min(15.0, home_xr_v4 + half)),
        max(0.5, min(15.0, away_xr_v4 + half)),
    )


def build_bullpen_strength():
    """Load team bullpen stats keyed by team_name (current season only)."""
    season = datetime.now(ZoneInfo("America/Toronto")).year
    try:
        rows = (
            supabase.table("mlb_bullpen_strength")
            .select("team_name,shrunk_ra9_index,bullpen_ip")
            .eq("season", season)
            .execute()
            .data
        )
        return {r["team_name"]: r for r in rows}
    except Exception:
        return {}


def _parse_ip_str(ip_str):
    """'69.1' → 69.333 (baseball IP notation: tenths = outs, not decimal thirds)."""
    try:
        parts = str(ip_str).split(".")
        full = int(parts[0])
        outs = int(parts[1]) if len(parts) > 1 else 0
        return full + outs / 3.0
    except Exception:
        return 0.0


def compute_xr_v3(home_pitcher, away_pitcher, home_bp, away_bp,
                  h_score, a_score, h_allow, a_allow, league_avg):
    """
    Expected runs with explicit starter/bullpen innings split.

    Defensive quality = (starter_fraction * starter_def) + (bullpen_fraction * bullpen_def)
    where each def factor = PITCHER_WEIGHT * personnel_ra9_index + (1-PITCHER_WEIGHT) * team_allow_index
    """
    def _ip_per_start(pitcher):
        if not pitcher:
            return DEFAULT_STARTER_IP
        gs = int(pitcher.get("games_started") or 0)
        ip = _parse_ip_str(pitcher.get("innings_pitched") or "0")
        if gs > 0 and ip > 0:
            return max(4.0, min(7.5, ip / gs))
        return DEFAULT_STARTER_IP

    def _p_idx(pitcher):
        if not pitcher:
            return None
        v = pitcher.get("shrunk_ra9_index")
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _bp_idx(bp):
        if not bp:
            return 1.0
        try:
            return float(bp.get("shrunk_ra9_index") or 1.0)
        except (TypeError, ValueError):
            return 1.0

    # Away pitcher faces home offense; home pitcher faces away offense
    away_ips = _ip_per_start(away_pitcher)
    home_ips = _ip_per_start(home_pitcher)

    away_sf = away_ips / 9.0          # away starter's fraction of game
    home_sf = home_ips / 9.0

    away_pi = _p_idx(away_pitcher)
    home_pi = _p_idx(home_pitcher)

    # Defensive factors for each component
    away_starter_def = (PITCHER_WEIGHT * away_pi + (1 - PITCHER_WEIGHT) * a_allow) if away_pi is not None else a_allow
    away_bp_def = PITCHER_WEIGHT * _bp_idx(away_bp) + (1 - PITCHER_WEIGHT) * a_allow

    home_starter_def = (PITCHER_WEIGHT * home_pi + (1 - PITCHER_WEIGHT) * h_allow) if home_pi is not None else h_allow
    home_bp_def = PITCHER_WEIGHT * _bp_idx(home_bp) + (1 - PITCHER_WEIGHT) * h_allow

    a_def_v3 = away_sf * away_starter_def + (1 - away_sf) * away_bp_def
    h_def_v3 = home_sf * home_starter_def + (1 - home_sf) * home_bp_def

    home_xr = max(0.5, min(15.0, league_avg * h_score * a_def_v3 * HOME_ADV))
    away_xr = max(0.5, min(15.0, league_avg * a_score * h_def_v3))
    return home_xr, away_xr


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
    bullpens = build_bullpen_strength()
    has_bullpen = bool(bullpens)

    batter_splits, game_lineups, pitcher_hands = build_lineup_data(today)
    has_lineup = bool(batter_splits)

    seen = set()
    saved = 0
    saved_v3 = 0
    saved_v4 = 0
    saved_v5 = 0
    weather_cache = {}    # (lat, lon, game_date) → weather tuple | None

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

        # --- v3 + v4 shadow predictions (production v2 unchanged) ---
        if has_bullpen:
            home_bp = bullpens.get(home)
            away_bp = bullpens.get(away)

            # v3: bullpen-aware defense, team-level offense
            home_xr_v3, away_xr_v3 = compute_xr_v3(
                home_pitcher, away_pitcher, home_bp, away_bp,
                h_score, a_score, h_allow, a_allow, league_avg,
            )
            m_v3 = markets_from_matrix(
                build_run_matrix(home_xr_v3, away_xr_v3), home_xr_v3, away_xr_v3
            )
            row_v3 = {
                "game_id": gid,
                "model_version": MODEL_VERSION_BP,
                "home_team_name": home,
                "away_team_name": away,
                "expected_home_runs": round(home_xr_v3, 3),
                "expected_away_runs": round(away_xr_v3, 3),
                "expected_total_runs": round(home_xr_v3 + away_xr_v3, 3),
                **m_v3,
            }
            supabase.table("mlb_run_predictions").upsert(
                row_v3, on_conflict="game_id,model_version"
            ).execute()
            saved_v3 += 1

            # v4: v3 defense + lineup-aware offense (falls back to team avg when no lineup)
            home_off = _lineup_offense_factor(
                gid, "home", "away", batter_splits, game_lineups, pitcher_hands
            )
            away_off = _lineup_offense_factor(
                gid, "away", "home", batter_splits, game_lineups, pitcher_hands
            )
            home_xr_v4, away_xr_v4 = compute_xr_v4(
                home_pitcher, away_pitcher, home_bp, away_bp,
                h_score, a_score, h_allow, a_allow, league_avg,
                home_off_factor=home_off,
                away_off_factor=away_off,
            )
            m_v4 = markets_from_matrix(
                build_run_matrix(home_xr_v4, away_xr_v4), home_xr_v4, away_xr_v4
            )
            row_v4 = {
                "game_id": gid,
                "model_version": MODEL_VERSION_LU,
                "home_team_name": home,
                "away_team_name": away,
                "expected_home_runs": round(home_xr_v4, 3),
                "expected_away_runs": round(away_xr_v4, 3),
                "expected_total_runs": round(home_xr_v4 + away_xr_v4, 3),
                **m_v4,
            }
            supabase.table("mlb_run_predictions").upsert(
                row_v4, on_conflict="game_id,model_version"
            ).execute()
            saved_v4 += 1

            # v5: v4 + park factors + weather (Open-Meteo, outdoor stadiums only)
            park_run_adj, is_covered, lat, lon, cf_bearing = _team_to_stadium_info(home)

            weather_result = None
            if not is_covered and lat is not None:
                game_date_str = g.get("game_date", today.isoformat())
                game_hour = _game_hour_utc(g.get("start_time_utc"))
                weather_result = _fetch_weather_open_meteo(
                    lat, lon, game_date_str, game_hour, weather_cache
                )

            temp_c = wind_kmh = wind_dir_from = None
            if weather_result:
                temp_c, wind_kmh, wind_dir_from = weather_result

            w_adj = (
                _weather_adj(temp_c, wind_kmh, wind_dir_from, cf_bearing)
                if not is_covered else 0.0
            )
            env_adj_total = park_run_adj + w_adj

            home_xr_v5, away_xr_v5 = compute_xr_v5(home_xr_v4, away_xr_v4, env_adj_total)
            m_v5 = markets_from_matrix(
                build_run_matrix(home_xr_v5, away_xr_v5), home_xr_v5, away_xr_v5
            )
            row_v5 = {
                "game_id": gid,
                "model_version": MODEL_VERSION_ENV,
                "home_team_name": home,
                "away_team_name": away,
                "expected_home_runs": round(home_xr_v5, 3),
                "expected_away_runs": round(away_xr_v5, 3),
                "expected_total_runs": round(home_xr_v5 + away_xr_v5, 3),
                **m_v5,
            }
            supabase.table("mlb_run_predictions").upsert(
                row_v5, on_conflict="game_id,model_version"
            ).execute()
            saved_v5 += 1

        h_data = "strength" if hs else "prior"
        a_data = "strength" if as_ else "prior"
        hp_label = f"{home_pitcher['pitcher_name']} idx={home_pitcher['shrunk_ra9_index']}" if home_pitcher else "TBD"
        ap_label = f"{away_pitcher['pitcher_name']} idx={away_pitcher['shrunk_ra9_index']}" if away_pitcher else "TBD"
        bp_note = ""
        if has_bullpen and saved_v3 > 0:
            h_bp = bullpens.get(home)
            a_bp = bullpens.get(away)
            h_bpidx = f"{h_bp['shrunk_ra9_index']}" if h_bp else "avg"
            a_bpidx = f"{a_bp['shrunk_ra9_index']}" if a_bp else "avg"
            bp_note = f" | BP idx: {home}={h_bpidx} {away}={a_bpidx}"
        lu_note = ""
        if has_lineup:
            home_off_disp = _lineup_offense_factor(
                gid, "home", "away", batter_splits, game_lineups, pitcher_hands
            )
            away_off_disp = _lineup_offense_factor(
                gid, "away", "home", batter_splits, game_lineups, pitcher_hands
            )
            if home_off_disp is not None or away_off_disp is not None:
                h_str = f"{home_off_disp:.3f}" if home_off_disp is not None else "avg"
                a_str = f"{away_off_disp:.3f}" if away_off_disp is not None else "avg"
                lu_note = f" | LU off: {home}={h_str} {away}={a_str}"
        env_note = ""
        if has_bullpen and saved_v5 > 0:
            _park_adj_disp, _covered_disp, *_ = _team_to_stadium_info(home)
            if _covered_disp:
                env_note = f" | park={_park_adj_disp:+.2f} [covered]"
            elif weather_result and temp_c is not None:
                env_note = (
                    f" | park={_park_adj_disp:+.2f} w={w_adj:+.2f}"
                    f" [{temp_c:.0f}°C {wind_kmh:.0f}km/h]"
                )
            else:
                env_note = f" | park={_park_adj_disp:+.2f} w=n/a"
        print(
            f"{home} vs {away} | xR {home_xr:.2f}-{away_xr:.2f} | "
            f"ML {m['home_win_probability']}/{m['away_win_probability']} | "
            f"O8.5 {m['over_85_probability']} | RL h-1.5 {m['home_rl_minus15_prob']} "
            f"[{h_data}/{a_data}]\n"
            f"  SP: {home}→{hp_label} | {away}→{ap_label}{bp_note}{lu_note}{env_note}"
        )

    print(
        f"\n✅ MLB Poisson run predictions saved: {saved} (v2) | "
        f"{saved_v3} (v3 bullpen) | {saved_v4} (v4 lineup) | {saved_v5} (v5 environment)"
    )


if __name__ == "__main__":
    main()
