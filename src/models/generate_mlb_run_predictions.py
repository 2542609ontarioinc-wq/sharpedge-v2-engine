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
import csv
import io
import math
import os
import requests
import time
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
MODEL_VERSION_FORM = "poisson_v6_form"
MODEL_VERSION_SC = "poisson_v7_statcast"
SPORT_KEY = "baseball_mlb"
PITCHER_WEIGHT = 0.6     # blend: 60% starting pitcher RA9 / 40% team defense
DEFAULT_STARTER_IP = 5.5  # historical MLB average IP/GS when starter data is missing

# v7 Statcast constants (2024/2025 MLB league averages)
LEAGUE_AVG_BARREL_PCT = 8.0    # league-average Barrel%
LEAGUE_AVG_HARDHIT_PCT = 38.0  # league-average Hard-Hit%
STATCAST_MAX_MULT = 0.05       # cap Statcast offense multiplier at ±5%
SAVANT_MIN_PA = 200            # full weight at 200+ PA; linearly shrunk below
_SAVANT_CACHE_FILE = "/tmp/sharpedge_savant_{year}.csv"

# Baseball Savant abbreviations keyed by our team-name substring
_SAVANT_TEAM_MAP = [
    ("white sox",   "CWS"),
    ("red sox",     "BOS"),
    ("blue jays",   "TOR"),
    ("diamondback", "ARI"),
    ("braves",      "ATL"),
    ("orioles",     "BAL"),
    ("cubs",        "CHC"),
    ("reds",        "CIN"),
    ("guardians",   "CLE"),
    ("rockies",     "COL"),
    ("tigers",      "DET"),
    ("astros",      "HOU"),
    ("royals",      "KC"),
    ("angels",      "LAA"),
    ("dodgers",     "LAD"),
    ("marlins",     "MIA"),
    ("brewers",     "MIL"),
    ("twins",       "MIN"),
    ("mets",        "NYM"),
    ("yankees",     "NYY"),
    ("athletics",   "ATH"),   # Sacramento Athletics 2025+; also try OAK below
    ("phillies",    "PHI"),
    ("pirates",     "PIT"),
    ("padres",      "SD"),
    ("mariners",    "SEA"),
    ("giants",      "SF"),
    ("cardinals",   "STL"),
    ("rays",        "TB"),
    ("rangers",     "TEX"),
    ("nationals",   "WSH"),
]
# Extra abbreviation aliases tried when primary lookup fails
_SAVANT_ALIASES = {"ATH": ["OAK", "SAC"], "CWS": ["CHW"]}


def _lookup_savant_abbr(team_name):
    tn = (team_name or "").lower()
    for kw, abbr in _SAVANT_TEAM_MAP:
        if kw in tn:
            return abbr
    return None


def _parse_savant_csv(text):
    """
    Parse Baseball Savant team-level statcast CSV.
    Returns dict: abbr → {barrel_pct, hardhit_pct, pa}.
    Tries multiple column-name variants to handle format changes.
    """
    BARREL_COLS = ["barrel_batted_rate", "brl_percent", "barrel_pct", "brl_pa", "barrel%"]
    HARDHIT_COLS = ["hard_hit_percent", "hardhit_percent", "hard_hit_pct", "hardhit%"]
    TEAM_COLS = ["last_name", "team_name_alt", "team_abbrev", "player_name", "team"]
    PA_COLS = ["pa", "ab", "batted_balls", "attempts"]

    reader = csv.DictReader(io.StringIO(text.strip()))
    header = reader.fieldnames or []
    hl = [c.lower().strip() for c in header]

    def _pick(candidates):
        for c in candidates:
            if c in hl:
                return header[hl.index(c)]
        return None

    barrel_col = _pick(BARREL_COLS)
    hardhit_col = _pick(HARDHIT_COLS)
    team_col = _pick(TEAM_COLS)
    pa_col = _pick(PA_COLS)

    if not barrel_col or not hardhit_col or not team_col:
        return {}

    result = {}
    for row in reader:
        abbr = (row.get(team_col) or "").strip().upper()
        if not abbr:
            continue
        try:
            barrel = float(row.get(barrel_col) or 0)
            hardhit = float(row.get(hardhit_col) or 0)
        except (TypeError, ValueError):
            continue
        pa = 0
        if pa_col:
            try:
                pa = int(float(row.get(pa_col) or 0))
            except (TypeError, ValueError):
                pa = 999  # assume adequate sample if column missing
        # Savant may store barrel as a decimal (0.08) rather than percent (8.0) —
        # normalise: values < 1.0 are treated as fractions
        if 0 < barrel < 1.0:
            barrel *= 100
        if 0 < hardhit < 1.0:
            hardhit *= 100
        result[abbr] = {"barrel_pct": barrel, "hardhit_pct": hardhit, "pa": pa}
    return result


def _fetch_savant_statcast(year):
    """
    Fetch team-level Barrel%/Hard-Hit% from Baseball Savant (free, no key).
    Caches to /tmp for one day — data updates slowly mid-season.
    Returns dict: abbr → {barrel_pct, hardhit_pct, pa}  or {} on any failure.
    Falls back to stale cache rather than crashing.
    """
    cache_file = _SAVANT_CACHE_FILE.format(year=year)
    today_str = datetime.now(ZoneInfo("America/Toronto")).date().isoformat()

    # Use valid cache from today
    if os.path.exists(cache_file):
        try:
            mtime_date = datetime.fromtimestamp(os.path.getmtime(cache_file)).date().isoformat()
            if mtime_date == today_str:
                with open(cache_file, encoding="utf-8") as f:
                    parsed = _parse_savant_csv(f.read())
                if parsed:
                    return parsed
        except Exception:
            pass

    url = (
        f"https://baseballsavant.mlb.com/leaderboard/statcast"
        f"?abs=0&type=batter-team&year={year}&position=&team=&min=0&csv=true"
    )
    try:
        resp = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SharpEdge/2.0)"},
        )
        if resp.status_code == 200 and resp.text.strip():
            parsed = _parse_savant_csv(resp.text)
            if parsed:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(resp.text)
                return parsed
            print(f"  Savant CSV fetched but no usable columns found — skipping v7 Statcast")
        else:
            print(f"  Savant fetch returned HTTP {resp.status_code} — skipping v7 Statcast")
    except Exception as e:
        print(f"  Savant fetch failed: {e} — skipping v7 Statcast")

    # Try stale cache as last resort
    if os.path.exists(cache_file):
        try:
            with open(cache_file, encoding="utf-8") as f:
                parsed = _parse_savant_csv(f.read())
            if parsed:
                print(f"  Using stale Savant cache for v7")
                return parsed
        except Exception:
            pass

    return {}


def _statcast_off_mult(team_name, savant_data):
    """
    Return a small offense multiplier for team_name based on Barrel% + Hard-Hit%.
    Returns 1.0 (no adjustment) if team not found or sample too small.
    Maximum adjustment: ±STATCAST_MAX_MULT (5%).
    """
    if not savant_data:
        return 1.0
    abbr = _lookup_savant_abbr(team_name)
    if not abbr:
        return 1.0
    row = savant_data.get(abbr)
    if row is None:
        # try known aliases
        for alias in _SAVANT_ALIASES.get(abbr, []):
            row = savant_data.get(alias)
            if row is not None:
                break
    if row is None:
        return 1.0

    barrel = row.get("barrel_pct", LEAGUE_AVG_BARREL_PCT)
    hardhit = row.get("hardhit_pct", LEAGUE_AVG_HARDHIT_PCT)
    pa = row.get("pa", SAVANT_MIN_PA)

    # Relative to league average (1.0 = average)
    barrel_rel = barrel / LEAGUE_AVG_BARREL_PCT if LEAGUE_AVG_BARREL_PCT > 0 else 1.0
    hardhit_rel = hardhit / LEAGUE_AVG_HARDHIT_PCT if LEAGUE_AVG_HARDHIT_PCT > 0 else 1.0
    combined_rel = (barrel_rel + hardhit_rel) / 2.0

    # Scale: ±10% from league avg in Statcast → ±STATCAST_MAX_MULT in runs
    raw_adj = (combined_rel - 1.0) * (STATCAST_MAX_MULT / 0.10)
    clamped = max(-STATCAST_MAX_MULT, min(STATCAST_MAX_MULT, raw_adj))

    # Shrink toward zero for small samples
    sample_weight = min(pa, SAVANT_MIN_PA) / max(SAVANT_MIN_PA, 1)
    return 1.0 + clamped * sample_weight


def compute_xr_v7(home_xr_v6, away_xr_v6, home_sc_mult, away_sc_mult):
    """
    v7 = v6 + Statcast quality-of-contact (Barrel% + Hard-Hit%) offense refinement.
    Applies a small multiplicative adjustment to each team's OFFENSIVE side only.
    """
    home_xr = max(0.5, min(15.0, home_xr_v6 * home_sc_mult))
    away_xr = max(0.5, min(15.0, away_xr_v6 * away_sc_mult))
    return home_xr, away_xr


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


# ---------------------------------------------------------------------------
# v6: Recent form (last-10 games) adjustment — MLB Stats API (free, keyless)
# ---------------------------------------------------------------------------

# (substring_in_lower_team_name, mlb_stats_api_team_id)
_MLB_TEAM_ID_MAP = [
    ("white sox",   145),
    ("red sox",     111),
    ("blue jays",   141),
    ("diamondback", 109),
    ("braves",      144),
    ("orioles",     110),
    ("cubs",        112),
    ("reds",        113),
    ("guardians",   114),
    ("rockies",     115),
    ("tigers",      116),
    ("astros",      117),
    ("royals",      118),
    ("angels",      108),
    ("dodgers",     119),
    ("marlins",     146),
    ("brewers",     158),
    ("twins",       142),
    ("mets",        121),
    ("yankees",     147),
    ("athletics",   133),
    ("phillies",    143),
    ("pirates",     134),
    ("padres",      135),
    ("mariners",    136),
    ("giants",      137),
    ("cardinals",   138),
    ("rays",        139),
    ("rangers",     140),
    ("nationals",   120),
]

FORM_RECENT_WEIGHT = 0.30   # 70% season / 30% recent; shrunk for < 10 games


def _lookup_mlb_team_id(team_name):
    tn = (team_name or "").lower()
    for keyword, tid in _MLB_TEAM_ID_MAP:
        if keyword in tn:
            return tid
    return None


def _fetch_recent_form(team_id, yesterday_str, season, cache, n_games=10):
    """
    Query MLB Stats API for the last n_games finished regular-season results.
    Returns (avg_rs, avg_ra, n_actual) or None on failure.
    Caches by team_id so each team is only fetched once per run.
    """
    if team_id in cache:
        return cache[team_id]
    try:
        start = (datetime.fromisoformat(yesterday_str) - timedelta(days=45)).isoformat()[:10]
        resp = requests.get(
            "https://statsapi.mlb.com/api/v1/schedule",
            params={
                "sportId": 1,
                "teamId": team_id,
                "startDate": start,
                "endDate": yesterday_str,
                "hydrate": "linescore",
                "gameType": "R",
                "season": season,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            cache[team_id] = None
            return None
        data = resp.json()
        games = []
        for date_block in (data.get("dates") or []):
            for game in (date_block.get("games") or []):
                if (game.get("status") or {}).get("abstractGameState") != "Final":
                    continue
                ls = game.get("linescore", {})
                ls_teams = ls.get("teams", {})
                home_runs = ls_teams.get("home", {}).get("runs")
                away_runs = ls_teams.get("away", {}).get("runs")
                if home_runs is None or away_runs is None:
                    continue
                home_tid = (game.get("teams", {}).get("home", {}).get("team", {}).get("id"))
                away_tid = (game.get("teams", {}).get("away", {}).get("team", {}).get("id"))
                if home_tid == team_id:
                    games.append((int(home_runs), int(away_runs)))
                elif away_tid == team_id:
                    games.append((int(away_runs), int(home_runs)))
        recent = games[-n_games:]
        if not recent:
            cache[team_id] = None
            return None
        result = (
            sum(g[0] for g in recent) / len(recent),  # avg runs scored
            sum(g[1] for g in recent) / len(recent),  # avg runs allowed
            len(recent),
        )
    except Exception:
        result = None
    cache[team_id] = result
    return result


def compute_xr_v6(home_xr_v5, away_xr_v5,
                   h_score, a_score, h_allow, a_allow,
                   home_form, away_form, league_avg):
    """
    v6 = v5 × multiplicative recent-form adjustment.

    For each team, blends season index (70%) with L10 rate (30%, shrunk by
    games available).  The multiplier = blended_idx / season_idx; applied to
    the offensive side of one team and the defensive side of the other, which
    is how they each contribute to a given team's expected runs.
    """
    def _mult(season_idx, recent_per_game, n_games):
        if recent_per_game is None or n_games == 0 or season_idx <= 0 or league_avg <= 0:
            return 1.0
        weight = FORM_RECENT_WEIGHT * min(n_games, 10) / 10.0
        recent_idx = recent_per_game / league_avg
        blended = (1.0 - weight) * season_idx + weight * recent_idx
        return blended / season_idx

    h_rs = home_form[0] if home_form else None
    h_ra = home_form[1] if home_form else None
    h_n  = home_form[2] if home_form else 0
    a_rs = away_form[0] if away_form else None
    a_ra = away_form[1] if away_form else None
    a_n  = away_form[2] if away_form else 0

    # home expected runs: home offense × away defense (each nudged by recent form)
    home_xr_v6 = max(0.5, min(15.0,
        home_xr_v5 * _mult(h_score, h_rs, h_n) * _mult(a_allow, a_ra, a_n)
    ))
    # away expected runs: away offense × home defense
    away_xr_v6 = max(0.5, min(15.0,
        away_xr_v5 * _mult(a_score, a_rs, a_n) * _mult(h_allow, h_ra, h_n)
    ))
    return home_xr_v6, away_xr_v6


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

    yesterday = (today - timedelta(days=1)).isoformat()
    season = today.year

    savant_data = _fetch_savant_statcast(season)
    has_statcast = bool(savant_data)
    if has_statcast:
        print(f"  Savant Statcast loaded: {len(savant_data)} teams")
    else:
        print("  Savant Statcast unavailable — v7 will equal v6")

    seen = set()
    saved = 0
    saved_v3 = 0
    saved_v4 = 0
    saved_v5 = 0
    saved_v6 = 0
    saved_v7 = 0
    weather_cache = {}    # (lat, lon, game_date) → weather tuple | None
    form_cache = {}       # team_id → (avg_rs, avg_ra, n) | None

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

            # v6: v5 + recent form (L10 games from MLB Stats API, free/keyless)
            home_tid = _lookup_mlb_team_id(home)
            away_tid = _lookup_mlb_team_id(away)
            home_form = _fetch_recent_form(home_tid, yesterday, season, form_cache) if home_tid else None
            away_form = _fetch_recent_form(away_tid, yesterday, season, form_cache) if away_tid else None

            home_xr_v6, away_xr_v6 = compute_xr_v6(
                home_xr_v5, away_xr_v5,
                h_score, a_score, h_allow, a_allow,
                home_form, away_form, league_avg,
            )
            m_v6 = markets_from_matrix(
                build_run_matrix(home_xr_v6, away_xr_v6), home_xr_v6, away_xr_v6
            )
            row_v6 = {
                "game_id": gid,
                "model_version": MODEL_VERSION_FORM,
                "home_team_name": home,
                "away_team_name": away,
                "expected_home_runs": round(home_xr_v6, 3),
                "expected_away_runs": round(away_xr_v6, 3),
                "expected_total_runs": round(home_xr_v6 + away_xr_v6, 3),
                **m_v6,
            }
            supabase.table("mlb_run_predictions").upsert(
                row_v6, on_conflict="game_id,model_version"
            ).execute()
            saved_v6 += 1

            # v7: v6 + Statcast quality-of-contact (Barrel% + Hard-Hit% from Baseball Savant)
            home_sc_mult = _statcast_off_mult(home, savant_data)
            away_sc_mult = _statcast_off_mult(away, savant_data)
            home_xr_v7, away_xr_v7 = compute_xr_v7(
                home_xr_v6, away_xr_v6, home_sc_mult, away_sc_mult
            )
            m_v7 = markets_from_matrix(
                build_run_matrix(home_xr_v7, away_xr_v7), home_xr_v7, away_xr_v7
            )
            row_v7 = {
                "game_id": gid,
                "model_version": MODEL_VERSION_SC,
                "home_team_name": home,
                "away_team_name": away,
                "expected_home_runs": round(home_xr_v7, 3),
                "expected_away_runs": round(away_xr_v7, 3),
                "expected_total_runs": round(home_xr_v7 + away_xr_v7, 3),
                **m_v7,
            }
            supabase.table("mlb_run_predictions").upsert(
                row_v7, on_conflict="game_id,model_version"
            ).execute()
            saved_v7 += 1

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
        form_note = ""
        if has_bullpen and saved_v6 > 0:
            h_f = home_form
            a_f = away_form
            h_str = f"L{h_f[2]}={h_f[0]:.1f}rs/{h_f[1]:.1f}ra" if h_f else "no-data"
            a_str = f"L{a_f[2]}={a_f[0]:.1f}rs/{a_f[1]:.1f}ra" if a_f else "no-data"
            v6_delta = (home_xr_v6 + away_xr_v6) - (home_xr_v5 + away_xr_v5)
            form_note = f" | form: {home}={h_str} {away}={a_str} Δtot={v6_delta:+.2f}"
        sc_note = ""
        if has_bullpen and saved_v7 > 0:
            h_m = home_sc_mult
            a_m = away_sc_mult
            v7_delta = (home_xr_v7 + away_xr_v7) - (home_xr_v6 + away_xr_v6)
            sc_note = (
                f" | SC: {home}×{h_m:.3f} {away}×{a_m:.3f} Δtot={v7_delta:+.3f}"
                if has_statcast else " | SC: no-data"
            )
        print(
            f"{home} vs {away} | xR {home_xr:.2f}-{away_xr:.2f} | "
            f"ML {m['home_win_probability']}/{m['away_win_probability']} | "
            f"O8.5 {m['over_85_probability']} | RL h-1.5 {m['home_rl_minus15_prob']} "
            f"[{h_data}/{a_data}]\n"
            f"  SP: {home}→{hp_label} | {away}→{ap_label}{bp_note}{lu_note}{env_note}{form_note}{sc_note}"
        )

    print(
        f"\n✅ MLB Poisson run predictions saved: {saved} (v2) | "
        f"{saved_v3} (v3 bullpen) | {saved_v4} (v4 lineup) | "
        f"{saved_v5} (v5 environment) | {saved_v6} (v6 form) | "
        f"{saved_v7} (v7 statcast)"
    )


if __name__ == "__main__":
    main()
