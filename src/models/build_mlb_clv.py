"""
Compute closing-line value (CLV) for graded MLB game picks.

CLV = closing_novig_prob - opening_novig_prob  (both in percentage points, e.g. 52.3)
Positive CLV: the market moved toward our pick after we published it — we beat the close.
Negative CLV: the market moved against our pick — sharp money disagreed.
Zero / near-zero: market was efficient at our entry.

CLV is the real edge signal.  Win-rate tells you what happened.
CLV tells you whether your process was sound before the result was known.

--- Honesty rules ---
- Picks without a real opening novig (edge_flag='no-odds') are EXCLUDED from CLV stats.
- Picks with no closing snapshot (alternate-line safe-zone picks, games with no hourly
  snapshot before first pitch) are EXCLUDED — not counted as 0.
- VOID picks are EXCLUDED.
- Player props are EXCLUDED (no clean 2-sided de-vig available at closing).

--- Data sources ---
Opening novig:
  game picks (moneyline/totals/run_line): mlb_final_predictions.market_implied_probability
  safe zone picks: mlb_safe_zone.balanced_novig_pct / banker_novig_pct
Closing novig:
  mlb_odds_snapshots — last bulk snapshot (h2h/totals/spreads) before commence_time.
  Alternate markets (alternate_totals, alternate_spreads) may not have a closing snapshot
  if the pick was generated from an alternate line in the morning.

Writes:
  mlb_clv_tracking: per-pick CLV rows (upsert on game_id, market, pick).
  mlb_pick_results: avg_clv, clv_positive_count, clv_sample_size (update only).
"""
from collections import defaultdict
from datetime import datetime, timezone

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Market buckets that appear in mlb_pick_results.
MARKET_BUCKETS = ["overall", "moneyline", "totals", "run_line", "safe_balanced", "safe_banker"]
_SAFE_ZONE_MARKETS = {"safe_balanced", "safe_banker"}


def _num(v, default=None):
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Parse a pick string into (snap_markets, selection_key, line_value)
# so we can look it up in mlb_odds_snapshots.
#
# snap_markets: tuple of Odds API market keys to search
# selection_key: lowercase selection string to match (team name, 'over', 'under')
# line_value: float or None (None = 2-way market with no line, i.e. h2h)
# ---------------------------------------------------------------------------

def _parse_pick(market, pick):
    """Return (snap_market_keys, selection_key, line_value) or (None, None, None)."""
    p = (pick or "").strip()
    pl = p.lower()
    m = (market or "").lower()

    # Safe-zone step-back to moneyline: "{Team} moneyline"
    if pl.endswith(" moneyline"):
        team = p[: -len(" moneyline")].strip()
        return ("h2h",), team.lower(), None

    # Over/Under (totals or alternate totals)
    if pl.startswith("over ") or pl.startswith("under "):
        parts = pl.split()
        side = parts[0]  # 'over' or 'under'
        try:
            line = float(parts[1])
        except (IndexError, ValueError):
            return None, None, None
        # snap_mlb_odds_closing only captures standard 'totals', not 'alternate_totals'.
        # Alternate lines (not 7.5/8.5/9.5) will simply find no match → excluded from CLV.
        return ("totals", "alternate_totals"), side, line

    # Run-line or safe-zone with point spread: "{Team} -1.5" / "+1.5" / "+2.5"
    parts = p.rsplit(None, 1)
    if len(parts) == 2:
        try:
            line = float(parts[1])
            team = parts[0].strip()
            # snap_mlb_odds_closing only captures 'spreads' (standard ±1.5).
            # +2.5 is alternate_spreads and will find no match → excluded from CLV.
            return ("spreads", "alternate_spreads"), team.lower(), line
        except ValueError:
            pass

    # Moneyline game pick: plain team name
    if m == "moneyline":
        return ("h2h",), pl, None

    return None, None, None


# ---------------------------------------------------------------------------
# De-vig helpers (same logic as build_mlb_final_picks.py)
# ---------------------------------------------------------------------------

def _devig_h2h(rows_by_sel):
    """Given {selection_lower: odds_decimal}, return no-vig implied prob dict or None."""
    if len(rows_by_sel) < 2:
        return None
    total = sum(1.0 / d for d in rows_by_sel.values() if d and d > 1.0)
    if total <= 0:
        return None
    return {sel: round((1.0 / d / total) * 100, 4) for sel, d in rows_by_sel.items() if d and d > 1.0}


# ---------------------------------------------------------------------------
# Resolve closing novig from snapshot rows
# ---------------------------------------------------------------------------

def _closing_novig(game_snaps, market, pick, commence_time_str):
    """
    Return (novig_pct, odds_decimal, captured_at_str) or (None, None, None).

    game_snaps: all mlb_odds_snapshots rows for this game_id.
    Filters to snapshots captured strictly before commence_time.
    Uses the latest snapshot batch that contains a complete 2-sided market.
    """
    snap_markets, sel_key, pick_line = _parse_pick(market, pick)
    if not snap_markets or not sel_key:
        return None, None, None

    # Filter to market keys and (if applicable) matching line.
    relevant = [
        s for s in game_snaps
        if (s.get("market") or "") in snap_markets
    ]
    if pick_line is not None:
        relevant = [
            s for s in relevant
            if s.get("line") is not None and abs(_num(s.get("line"), 999) - pick_line) < 0.01
        ]

    # Filter to before first pitch (if commence_time is known).
    if commence_time_str:
        relevant = [s for s in relevant if (s.get("captured_at") or "") < commence_time_str]

    if not relevant:
        return None, None, None

    # Group by (bookmaker, captured_at) — all rows from one run share the same captured_at.
    by_book_time: dict[tuple, list] = defaultdict(list)
    for s in relevant:
        key = (s.get("bookmaker"), s.get("captured_at") or "")
        by_book_time[key].append(s)

    # Find the latest captured_at that has a complete 2-sided market.
    # Sort candidate (bookmaker, time) pairs by time descending.
    sorted_keys = sorted(by_book_time.keys(), key=lambda k: k[1], reverse=True)

    for (book, at), rows in [(k, by_book_time[k]) for k in sorted_keys]:
        by_sel = {}
        for r in rows:
            sel = (r.get("selection") or "").lower().strip()
            dec = _num(r.get("odds_decimal"))
            if sel and dec and dec > 1.0:
                by_sel[sel] = dec

        if len(by_sel) < 2:
            continue

        novig_map = _devig_h2h(by_sel)
        if novig_map is None:
            continue

        # For h2h / run-line picks: match by team name.
        # For totals: match by 'over' / 'under'.
        if sel_key in novig_map:
            return novig_map[sel_key], by_sel.get(sel_key), at

        # Fuzzy match for team names (Odds API names can differ from pick strings).
        for sel_lower, novig_pct in novig_map.items():
            if sel_key in sel_lower or sel_lower in sel_key:
                return novig_pct, by_sel.get(sel_lower), at

    return None, None, None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Load graded picks (WIN or LOSS only — VOIDs have no bet to evaluate).
    grades = (
        supabase.table("mlb_pick_grades")
        .select("game_id,market,pick,odds_decimal,edge_flag,no_odds,grade,home_team_name,away_team_name")
        .in_("grade", ["WIN", "LOSS"])
        .execute()
        .data
    )

    if not grades:
        print("No graded picks found.")
        print("✅ MLB CLV: 0 picks processed")
        return

    # Load opening novig sources.
    fp_rows = supabase.table("mlb_final_predictions").select(
        "game_id,market_implied_probability,odds_decimal,updated_at"
    ).execute().data
    fp_by_game = {r["game_id"]: r for r in fp_rows}

    sz_rows = supabase.table("mlb_safe_zone").select(
        "game_id,balanced_novig_pct,balanced_odds_decimal,banker_novig_pct,banker_odds_decimal,updated_at"
    ).execute().data
    sz_by_game = {r["game_id"]: r for r in sz_rows}

    # Load all snapshots for games that have graded picks.
    game_ids = list({g["game_id"] for g in grades if g.get("game_id")})
    snap_rows = []
    for i in range(0, len(game_ids), 100):
        chunk = game_ids[i:i + 100]
        snap_rows.extend(
            supabase.table("mlb_odds_snapshots")
            .select("game_id,market,selection,line,bookmaker,odds_decimal,commence_time,captured_at")
            .in_("game_id", chunk)
            .execute()
            .data
        )

    # Group snapshots by game_id.
    snaps_by_game: dict[str, list] = defaultdict(list)
    for s in snap_rows:
        gid = s.get("game_id")
        if gid:
            snaps_by_game[gid].append(s)

    # Also pull the commence_time from snapshots (games table only has game_date).
    commence_by_game = {}
    for gid, snaps in snaps_by_game.items():
        for s in snaps:
            ct = s.get("commence_time")
            if ct:
                commence_by_game[gid] = ct
                break

    now = datetime.now(timezone.utc).isoformat()
    clv_rows = []
    skipped_no_opening = 0
    skipped_no_closing = 0

    for g in grades:
        gid = g.get("game_id")
        market = (g.get("market") or "").lower()
        pick = g.get("pick")

        if not gid or not market or not pick:
            continue

        # Skip no-odds picks — we don't have a real opening novig.
        if g.get("no_odds") or (g.get("edge_flag") or "") == "no-odds":
            skipped_no_opening += 1
            continue

        # --- Opening novig ---
        opening_novig = None
        opening_odds = None
        opening_at = None

        if market in ("moneyline", "totals", "run_line"):
            fp = fp_by_game.get(gid)
            if fp:
                opening_novig = _num(fp.get("market_implied_probability"))
                opening_odds = _num(fp.get("odds_decimal"))
                opening_at = fp.get("updated_at")

        elif market == "safe_balanced":
            sz = sz_by_game.get(gid)
            if sz:
                opening_novig = _num(sz.get("balanced_novig_pct"))
                opening_odds = _num(sz.get("balanced_odds_decimal"))
                opening_at = sz.get("updated_at")

        elif market == "safe_banker":
            sz = sz_by_game.get(gid)
            if sz:
                opening_novig = _num(sz.get("banker_novig_pct"))
                opening_odds = _num(sz.get("banker_odds_decimal"))
                opening_at = sz.get("updated_at")

        if opening_novig is None:
            skipped_no_opening += 1
            continue

        # --- Closing novig ---
        game_snaps = snaps_by_game.get(gid, [])
        commence = commence_by_game.get(gid)

        closing_novig, closing_odds, closing_at = _closing_novig(game_snaps, market, pick, commence)

        if closing_novig is None:
            skipped_no_closing += 1
            continue

        clv = round(closing_novig - opening_novig, 4)

        clv_rows.append({
            "game_id": gid,
            "market": market,
            "pick": pick,
            "opening_novig_prob": round(opening_novig, 4),
            "opening_odds_decimal": round(opening_odds, 4) if opening_odds else None,
            "opening_captured_at": opening_at,
            "closing_novig_prob": round(closing_novig, 4),
            "closing_odds_decimal": round(closing_odds, 4) if closing_odds else None,
            "closing_captured_at": closing_at,
            "clv": clv,
            "beat_close": clv > 0,
            "computed_at": now,
        })

    # Upsert per-pick CLV rows.
    for row in clv_rows:
        supabase.table("mlb_clv_tracking").upsert(row, on_conflict="game_id,market,pick").execute()

    print(f"  CLV computed: {len(clv_rows)} picks")
    print(f"  Excluded (no opening novig / no-odds): {skipped_no_opening}")
    print(f"  Excluded (no closing snapshot): {skipped_no_closing}")

    # --- Aggregate CLV into mlb_pick_results ---
    # Build per-market buckets matching the grade_mlb_results grouping.
    buckets: dict[str, list[float]] = {k: [] for k in MARKET_BUCKETS}

    for row in clv_rows:
        mkt = row["market"]
        clv_val = row["clv"]
        if mkt not in _SAFE_ZONE_MARKETS:
            buckets["overall"].append(clv_val)
        if mkt in buckets:
            buckets[mkt].append(clv_val)

    print(f"\n  {'market':<14} {'sample':>7}  {'avg CLV':>9}  {'beat close':>11}")
    for market_key, vals in buckets.items():
        if not vals:
            continue
        avg = round(sum(vals) / len(vals), 4)
        positive = sum(1 for v in vals if v > 0)
        print(f"  {market_key:<14} {len(vals):>7}  {avg:>+9.3f}pp  {positive}/{len(vals)}")

        supabase.table("mlb_pick_results").update({
            "avg_clv": avg,
            "clv_positive_count": positive,
            "clv_sample_size": len(vals),
        }).eq("market", market_key).execute()

    print(f"\n✅ MLB CLV: {len(clv_rows)} picks computed | {skipped_no_opening + skipped_no_closing} excluded (no data)")


if __name__ == "__main__":
    main()
