"""
Generate MLB player prop predictions with market-anchored calibration.

Pitcher props (from mlb_pitchers.raw_stats — season stats already ingested):
  strikeouts     — K/9 × avg_IP; Poisson model; confidence 'solid'
  outs_recorded  — avg_IP × 3;   Poisson model; confidence 'solid'
  earned_runs    — ERA × avg_IP / 9; Poisson model; confidence 'noisier' (high per-start variance)
  hits_allowed   — H/GS; Poisson model; confidence 'noisier'
  walks          — BB/GS; Poisson model; confidence 'noisier'

Batter props (from mlb_lineups — confirmed lineup + season hitting stats):
  h_r_rbi        — (H+R+RBI)/GS; Poisson(λ) model; confidence 'solid'
                   Primary line = 0.5 (Over 0.5 = player gets ≥ 1 combined).
                   If market posts a different line, that line is used instead.

Calibration:
  calibrated_over_prob = 0.3 × model_over_prob + 0.7 × market_novig_over_prob
  If no market odds: calibrated_over_prob = model_over_prob; edge_flag = 'no-odds'.

Edge flag:
  REAL    — no-vig resolved AND edge in [-5, 10] (sane band)
  suspect — edge outside that range (model / market disagreement too large)
  no-odds — market odds not available for this player+market

Tiers (across all props globally by calibrated confidence × quality score):
  Bet of the Day | Elite | Standard
"""
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

TORONTO = ZoneInfo("America/Toronto")
SPORT_KEY = "baseball_mlb"
MODEL_WEIGHT = 0.3
MARKET_WEIGHT = 0.7
MIN_STARTS = 2       # require at least 2 GS to publish pitcher props
MIN_GAMES_BATTER = 5


# ─── Helpers ────────────────────────────────────────────────────────────────

def _safe(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_ip(s):
    """'83.2' means 83 full innings + 2 outs = 83.667 actual innings."""
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


def _decimal_to_american(dec):
    if not dec or dec <= 1:
        return None
    return int((dec - 1) * 100) if dec >= 2 else int(-100 / (dec - 1))


def poisson_cdf(k, lam):
    """P(X ≤ k) for X ~ Poisson(lam)."""
    if lam <= 0:
        return 1.0
    total = 0.0
    log_lam = math.log(lam)
    log_factorial = 0.0
    for i in range(int(k) + 1):
        if i > 0:
            log_factorial += math.log(i)
        total += math.exp(-lam + i * log_lam - log_factorial)
    return min(1.0, total)


def over_prob(line, lam):
    """P(X > line) = P(X ≥ ceil(line+ε)) for Poisson(lam), returned as 0-100."""
    threshold = math.floor(line)   # largest int that does NOT beat the line
    p = 1.0 - poisson_cdf(threshold, lam)
    return round(max(0.0, min(100.0, p * 100)), 2)


def natural_line(projection):
    """Fair no-market line: floor(proj) + 0.5 puts the model roughly at 50%."""
    return math.floor(projection) + 0.5


# ─── Market odds helpers ─────────────────────────────────────────────────────

def _match_player(prop_odds, player_name, market_key):
    """Return rows for this player + market. Falls back to last-name match."""
    name_lower = player_name.lower().strip()
    rows = [
        o for o in prop_odds
        if o.get("market_key") == market_key
        and (o.get("player_description") or "").lower().strip() == name_lower
    ]
    if not rows:
        last = name_lower.split()[-1] if name_lower else ""
        rows = [
            o for o in prop_odds
            if o.get("market_key") == market_key
            and last in (o.get("player_description") or "").lower().strip().split()
        ]
    return rows


def _consensus_line(rows):
    """Most-posted line across bookmakers."""
    lines = [float(o["line"]) for o in rows if o.get("line") is not None]
    return Counter(lines).most_common(1)[0][0] if lines else None


def _novig_and_best_odds(rows, line, want_side):
    """
    Returns (novig_over_pct, best_side_decimal, best_side_american) at the given line.
    want_side: 'over' or 'under' — determines which side's best decimal to return.
    """
    matching = [
        o for o in rows
        if o.get("line") is not None and abs(float(o["line"]) - line) < 0.01
        and o.get("odds_decimal") and float(o["odds_decimal"]) > 1.0
    ]

    by_book = defaultdict(dict)
    for o in matching:
        side = (o.get("side") or "").lower()
        by_book[o.get("bookmaker")][side] = float(o["odds_decimal"])

    novig_over = None
    for sides in by_book.values():
        if "over" in sides and "under" in sides:
            p_ov = 1 / sides["over"]
            p_un = 1 / sides["under"]
            total = p_ov + p_un
            if total > 0:
                novig_over = round(p_ov / total * 100, 2)
                break

    best_dec = None
    for o in matching:
        if (o.get("side") or "").lower() == want_side:
            d = float(o["odds_decimal"])
            if best_dec is None or d > best_dec:
                best_dec = d

    best_am = _decimal_to_american(best_dec) if best_dec else None
    return novig_over, best_dec, best_am


# ─── Projections ─────────────────────────────────────────────────────────────

def _pitcher_projections(pitcher_row):
    """Per-start stat projections from raw_stats and stored columns."""
    stats = pitcher_row.get("raw_stats") or {}
    gs = max(1, int(pitcher_row.get("games_started") or 0))

    ip_str = pitcher_row.get("innings_pitched") or str(stats.get("inningsPitched") or "")
    total_ip = _parse_ip(ip_str)
    avg_ip = (total_ip / gs) if (total_ip and gs > 0) else 5.0

    if gs >= MIN_STARTS:
        k_proj = int(stats.get("strikeOuts") or 0) / gs
        h_proj = int(stats.get("hits") or 0) / gs
        bb_proj = int(stats.get("baseOnBalls") or 0) / gs
        er_proj = int(stats.get("earnedRuns") or 0) / gs
    else:
        k9 = _safe(stats.get("strikeoutsPer9Inn"), 8.5)
        h9 = _safe(stats.get("hitsPer9Inn"), 8.5)
        bb9 = _safe(stats.get("walksPer9Inn"), 3.0)
        era = _safe(stats.get("era"), 4.5)
        k_proj = k9 * avg_ip / 9
        h_proj = h9 * avg_ip / 9
        bb_proj = bb9 * avg_ip / 9
        er_proj = era * avg_ip / 9

    return {
        "strikeouts":    round(k_proj, 2),
        "outs_recorded": round(avg_ip * 3, 2),
        "earned_runs":   round(er_proj, 2),
        "hits_allowed":  round(h_proj, 2),
        "walks":         round(bb_proj, 2),
    }


# ─── Prop row builder ─────────────────────────────────────────────────────────

PITCHER_MARKETS = [
    ("pitcher_strikeouts",  "strikeouts",    "solid"),
    ("pitcher_outs",        "outs_recorded", "solid"),   # Odds API key is 'pitcher_outs'
    ("pitcher_earned_runs", "earned_runs",   "noisier"),
    ("pitcher_hits_allowed","hits_allowed",  "noisier"),
    ("pitcher_walks",       "walks",         "noisier"),
]

BATTER_MARKETS = [
    ("batter_hits_runs_rbis", "h_r_rbi", "solid"),
]


def _build_prop_row(
    game_id, game_date, player_name, player_mlb_id, player_type,
    team_name, side, prop_market, proj, prop_odds, odds_key, confidence_note
):
    matched_rows = _match_player(prop_odds, player_name, odds_key)
    market_line = _consensus_line(matched_rows) if matched_rows else None

    if market_line is None:
        # No market coverage — use natural line, show raw model prob, flag no-odds
        mline = natural_line(proj)
        model_p = over_prob(mline, proj)
        cal_p = model_p
        pick_s = "Over" if cal_p >= 50 else "Under"
        return {
            "game_id": game_id,
            "game_date": game_date,
            "player_name": player_name,
            "player_mlb_id": player_mlb_id,
            "player_type": player_type,
            "team_name": team_name,
            "side": side,
            "prop_market": prop_market,
            "model_projection": proj,
            "market_line": mline,
            "model_over_prob": model_p,
            "market_novig_over_prob": None,
            "calibrated_over_prob": cal_p,
            "pick_side": pick_s,
            "best_odds_decimal": None,
            "best_odds_american": None,
            "model_edge": None,
            "edge_flag": "no-odds",
            "confidence_note": confidence_note,
            "confidence_tier": "Standard",
            "updated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        }

    model_p = over_prob(market_line, proj)
    novig_over, best_over_dec, best_over_am = _novig_and_best_odds(matched_rows, market_line, "over")
    novig_under, best_under_dec, best_under_am = _novig_and_best_odds(matched_rows, market_line, "under")

    if novig_over is None:
        cal_p = round(MODEL_WEIGHT * model_p + MARKET_WEIGHT * 50, 2)
        edge = None
        flag = "no-odds"
    else:
        cal_p = round(MODEL_WEIGHT * model_p + MARKET_WEIGHT * novig_over, 2)
        edge = round(cal_p - novig_over, 2)
        flag = "REAL" if -5 <= edge <= 10 else "suspect"

    pick_s = "Over" if cal_p >= 50 else "Under"
    if pick_s == "Over":
        pick_dec, pick_am = best_over_dec, best_over_am
    else:
        pick_dec, pick_am = best_under_dec, best_under_am

    return {
        "game_id": game_id,
        "game_date": game_date,
        "player_name": player_name,
        "player_mlb_id": player_mlb_id,
        "player_type": player_type,
        "team_name": team_name,
        "side": side,
        "prop_market": prop_market,
        "model_projection": proj,
        "market_line": market_line,
        "model_over_prob": model_p,
        "market_novig_over_prob": novig_over,
        "calibrated_over_prob": cal_p,
        "pick_side": pick_s,
        "best_odds_decimal": pick_dec,
        "best_odds_american": pick_am,
        "model_edge": edge,
        "edge_flag": flag,
        "confidence_note": confidence_note,
        "confidence_tier": "Standard",
        "updated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
    }


# ─── Tier assignment ──────────────────────────────────────────────────────────

def _assign_tiers(rows):
    """Sort all prop rows by quality score; label Bet of the Day / Elite / Standard."""
    def _score(r):
        conf = abs(_safe(r.get("calibrated_over_prob"), 50) - 50)
        flag = r.get("edge_flag", "")
        note = r.get("confidence_note", "")
        q = 1.5 if flag == "REAL" else (0.5 if flag == "no-odds" else 0.0)
        solid = 1.0 if note == "solid" else 0.7
        return conf * q * solid

    rows.sort(key=_score, reverse=True)
    for i, r in enumerate(rows):
        if i == 0:
            r["confidence_tier"] = "Bet of the Day"
        elif i < 6:
            r["confidence_tier"] = "Elite"
        else:
            r["confidence_tier"] = "Standard"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    today = datetime.now(TORONTO).date()
    window_end = (today + timedelta(days=3)).isoformat()

    # Purge upcoming props before regenerating so stale rows from prior runs don't linger.
    # Past game rows (game_date < today) are kept for grading.
    supabase.table("mlb_player_props").delete().gte("game_date", today.isoformat()).execute()

    prop_odds = supabase.table("mlb_player_prop_odds").select("*").execute().data
    # Only odds with a real game_id are usable (null means the game wasn't in our games table)
    prop_odds = [o for o in prop_odds if o.get("game_id") is not None]
    print(f"  Prop odds loaded: {len(prop_odds)} rows across "
          f"{len(set(o['game_id'] for o in prop_odds))} games")

    pitchers = (
        supabase.table("mlb_pitchers")
        .select("*")
        .gte("game_date", today.isoformat())
        .lte("game_date", window_end)
        .execute()
        .data
    )

    try:
        lineups = (
            supabase.table("mlb_lineups")
            .select("*")
            .gte("game_date", today.isoformat())
            .lte("game_date", window_end)
            .execute()
            .data
        )
    except Exception:
        lineups = []

    if not lineups:
        print("  No lineup rows in mlb_lineups — batter props skipped.")
        print("  Lineups post ~90 min before first pitch; re-run after ~5 PM ET to get batter props.")

    rows = []
    pitcher_skipped_no_odds = 0

    # ── Pitcher props ──────────────────────────────────────────────────────
    for p in pitchers:
        gs = int(p.get("games_started") or 0)
        pitcher_name = p.get("pitcher_name", "")
        if gs < MIN_STARTS:
            print(f"  Skip {pitcher_name}: {gs} GS (need ≥ {MIN_STARTS})")
            continue

        projections = _pitcher_projections(p)

        for odds_key, prop_market, confidence_note in PITCHER_MARKETS:
            proj = projections.get(prop_market)
            if proj is None or proj <= 0:
                continue

            # Only generate when the book actually posts odds for this pitcher+market.
            # Without real odds the 30/70 calibration is meaningless and the row
            # would appear in the frontend as a pick with no price — pure noise.
            if not _match_player(prop_odds, pitcher_name, odds_key):
                pitcher_skipped_no_odds += 1
                continue

            row = _build_prop_row(
                game_id=p["game_id"],
                game_date=p["game_date"],
                player_name=pitcher_name,
                player_mlb_id=p.get("pitcher_mlb_id"),
                player_type="pitcher",
                team_name=p.get("team_name"),
                side=p.get("side"),
                prop_market=prop_market,
                proj=proj,
                prop_odds=prop_odds,
                odds_key=odds_key,
                confidence_note=confidence_note,
            )
            rows.append(row)
            flag_label = f"[{row['edge_flag']}]"
            print(
                f"  {pitcher_name} {prop_market}: proj={proj:.1f} "
                f"line={row['market_line']} {row['pick_side']} "
                f"cal={row['calibrated_over_prob']}% {flag_label} {confidence_note}"
            )

    if pitcher_skipped_no_odds:
        print(f"  Pitchers skipped (no market odds): {pitcher_skipped_no_odds} market-slots")

    # ── Batter props ───────────────────────────────────────────────────────
    batter_skipped_no_odds = batter_skipped_low_gp = 0
    for batter in lineups:
        gp = int(batter.get("games_played") or 0)
        batter_name = batter.get("player_name", "")
        if gp < MIN_GAMES_BATTER:
            batter_skipped_low_gp += 1
            continue

        avg_hrr = _safe(batter.get("avg_hrr_per_game"), None)
        if avg_hrr is None or avg_hrr <= 0:
            continue

        # Only generate when the book lists this batter in the H+R+RBI market.
        if not _match_player(prop_odds, batter_name, "batter_hits_runs_rbis"):
            batter_skipped_no_odds += 1
            continue

        row = _build_prop_row(
            game_id=batter["game_id"],
            game_date=batter.get("game_date"),
            player_name=batter_name,
            player_mlb_id=batter.get("player_mlb_id"),
            player_type="batter",
            team_name=batter.get("team_name"),
            side=batter.get("side"),
            prop_market="h_r_rbi",
            proj=avg_hrr,
            prop_odds=prop_odds,
            odds_key="batter_hits_runs_rbis",
            confidence_note="solid",
        )
        rows.append(row)

    if batter_skipped_no_odds:
        print(f"  Batters skipped (not in book's H+R+RBI market): {batter_skipped_no_odds}")
    if batter_skipped_low_gp:
        print(f"  Batters skipped (< {MIN_GAMES_BATTER} GP): {batter_skipped_low_gp}")

    # ── Tier assignment and upsert ─────────────────────────────────────────
    _assign_tiers(rows)

    saved = 0
    for row in rows:
        try:
            supabase.table("mlb_player_props").upsert(
                row, on_conflict="game_id,player_mlb_id,prop_market"
            ).execute()
            saved += 1
        except Exception as e:
            print(f"  Failed: {row.get('player_name')} {row.get('prop_market')}: {e}")

    batter_saved = sum(1 for r in rows if r.get("player_type") == "batter")
    pitcher_saved = sum(1 for r in rows if r.get("player_type") == "pitcher")
    print(f"\n✅ MLB player props saved: {saved} ({pitcher_saved} pitchers, {batter_saved} batters)")


if __name__ == "__main__":
    main()
