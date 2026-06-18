"""
MLB final picks: multi-market selection + honest calibration + Safe Zone.

For each game that has run predictions:
  1. Build candidates for moneyline, totals, and run-line markets.
  2. Pick best/secondary by highest raw model confidence.
  3. Apply honest shrinkage: calibrated = 50 + (raw - 50) * 0.75
  4. Fetch no-vig implied probability from mlb_odds; compute edge; flag REAL/suspect/no-odds.
  5. Build MLB Safe Zone (softer pick derived from the sharp Poisson pick).
  6. Upsert mlb_final_predictions and mlb_safe_zone.

Safe Zone rules:
  Moneyline team X   → Balanced = X run-line +1.5 | Banker = X +2.5 (only if prob >= 80%)
  Total OVER  L      → Balanced = Over(L-1)        | Banker = Over(L-2) (only if prob >= 80%)
  Total UNDER L      → Balanced = Under(L+1)       | Banker = Under(L+2) (only if prob >= 80%)

Honest: NEVER show a banker unless the model probability for that line is >= 80%.
        NEVER invent an edge where there are no real odds — flag 'no-odds' instead.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SHRINK = 0.75
SPORT_KEY = "baseball_mlb"
MODEL_VERSION = "poisson_v2"
BANKER_THRESHOLD = 80.0


def _num(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _shrink(raw):
    return round(50 + (raw - 50) * SHRINK, 2)


# ---------------------------------------------------------------------------
# Candidate builders: one per market, returns dict or None
# ---------------------------------------------------------------------------

def _ml_candidates(pred, home, away):
    """Build moneyline candidates from run predictions."""
    hp = _num(pred.get("home_win_probability"))
    ap = _num(pred.get("away_win_probability"))
    cands = []
    if hp > 50:
        cands.append({"market": "moneyline", "pick": home, "raw_confidence": hp})
    if ap > 50:
        cands.append({"market": "moneyline", "pick": away, "raw_confidence": ap})
    return cands


def _totals_candidates(pred):
    """Return the best total pick (highest confidence away from 50%)."""
    lines = [
        (7.5, "over_75_probability",  "under_75_probability"),
        (8.5, "over_85_probability",  "under_85_probability"),
        (9.5, "over_95_probability",  "under_95_probability"),
    ]
    cands = []
    for line, ov_key, un_key in lines:
        ov = _num(pred.get(ov_key))
        un = _num(pred.get(un_key))
        if ov > 50:
            cands.append({"market": "totals", "pick": f"Over {line}", "raw_confidence": ov, "_line": line})
        if un > 50:
            cands.append({"market": "totals", "pick": f"Under {line}", "raw_confidence": un, "_line": line})
    # return the one with highest confidence
    if cands:
        return [max(cands, key=lambda c: c["raw_confidence"])]
    return []


def _runline_candidates(pred, home, away):
    """Return the most confident run-line pick (-1.5 only — sharper markets)."""
    h_m15 = _num(pred.get("home_rl_minus15_prob"))
    a_m15 = _num(pred.get("away_rl_minus15_prob"))
    cands = []
    if h_m15 > 50:
        cands.append({"market": "run_line", "pick": f"{home} -1.5", "raw_confidence": h_m15})
    if a_m15 > 50:
        cands.append({"market": "run_line", "pick": f"{away} -1.5", "raw_confidence": a_m15})
    if cands:
        return [max(cands, key=lambda c: c["raw_confidence"])]
    return []


# ---------------------------------------------------------------------------
# Odds / no-vig helpers
# ---------------------------------------------------------------------------

def _get_odds_rows(game_id):
    return (
        supabase.table("mlb_odds")
        .select("*")
        .eq("game_id", game_id)
        .execute()
        .data
    )


def _novig_for_moneyline(odds_rows, pick_team):
    """Return (novig_pct, odds_decimal) from the best 2-way h2h snapshot."""
    legs = [o for o in odds_rows if (o.get("market") or "").lower() == "h2h"]
    by_book = {}
    for o in legs:
        by_book.setdefault(o.get("bookmaker"), []).append(o)

    pick_lower = pick_team.lower().strip()
    for book, ol in by_book.items():
        by_sel = {}
        for o in ol:
            sel = (o.get("selection") or "").strip()
            dec = _num(o.get("odds_decimal"))
            if sel and dec > 1.0:
                by_sel[sel.lower()] = (dec, o)
        # h2h for MLB is 2-way (no draw)
        if len(by_sel) < 2:
            continue
        total = sum(1.0 / d for d, _ in by_sel.values())
        if total <= 0:
            continue
        if pick_lower in by_sel:
            dec, _ = by_sel[pick_lower]
            return (round((1.0 / dec / total) * 100, 2), dec)
    return None


def _novig_for_totals(odds_rows, pick):
    """Return (novig_pct, odds_decimal) for an Over/Under pick at the given line."""
    side = "over" if "over" in pick.lower() else "under"
    # parse line from pick string e.g. "Over 8.5" -> 8.5
    line = None
    for tok in pick.split():
        try:
            line = float(tok)
            break
        except ValueError:
            continue
    if line is None:
        return None

    legs = [o for o in odds_rows
            if (o.get("market") or "").lower() == "totals"
            and _num(o.get("line")) == line]
    by_book = {}
    for o in legs:
        by_book.setdefault(o.get("bookmaker"), []).append(o)

    for book, ol in by_book.items():
        by_sel = {(o.get("selection") or "").lower(): o for o in ol}
        if "over" in by_sel and "under" in by_sel:
            p_ov = 1.0 / _num(by_sel["over"]["odds_decimal"])
            p_un = 1.0 / _num(by_sel["under"]["odds_decimal"])
            total = p_ov + p_un
            if total <= 0:
                continue
            mine = p_ov if side == "over" else p_un
            dec = _num(by_sel[side]["odds_decimal"])
            return (round((mine / total) * 100, 2), dec)
    return None


def _novig_for_runline(odds_rows, pick):
    """Return (novig_pct, odds_decimal) for a run-line pick e.g. 'Yankees -1.5'."""
    # parse: last token is the line (e.g. '-1.5'), rest is team name
    parts = pick.rsplit(None, 1)
    if len(parts) != 2:
        return None
    team_name = parts[0].strip()
    try:
        line = float(parts[1])
    except ValueError:
        return None

    legs = [o for o in odds_rows
            if (o.get("market") or "").lower() == "spreads"
            and _num(o.get("line")) == line]
    by_book = {}
    for o in legs:
        by_book.setdefault(o.get("bookmaker"), []).append(o)

    tname_lower = team_name.lower().strip()
    for book, ol in by_book.items():
        by_sel = {}
        for o in ol:
            sel = (o.get("selection") or "").strip().lower()
            dec = _num(o.get("odds_decimal"))
            if sel and dec > 1.0:
                by_sel[sel] = (dec, o)
        if len(by_sel) < 2:
            continue
        total = sum(1.0 / d for d, _ in by_sel.values())
        if total <= 0:
            continue
        if tname_lower in by_sel:
            dec, _ = by_sel[tname_lower]
            return (round((1.0 / dec / total) * 100, 2), dec)
    return None


def _resolve_novig(odds_rows, market, pick):
    if market == "moneyline":
        return _novig_for_moneyline(odds_rows, pick)
    if market == "totals":
        return _novig_for_totals(odds_rows, pick)
    if market == "run_line":
        return _novig_for_runline(odds_rows, pick)
    return None


def _best_odds_decimal(odds_rows, market, pick):
    """Return best (highest) decimal odds for this pick, or None."""
    matches = []
    pick_lower = pick.lower().strip()
    for o in odds_rows:
        mkt = (o.get("market") or "").lower()
        sel = (o.get("selection") or "").lower().strip()
        dec = _num(o.get("odds_decimal"))
        if dec <= 1.0:
            continue
        if market == "moneyline" and mkt == "h2h" and sel == pick_lower:
            matches.append((dec, o))
        elif market == "totals" and mkt == "totals":
            side = "over" if "over" in pick_lower else "under"
            if sel == side:
                matches.append((dec, o))
        elif market == "run_line" and mkt == "spreads":
            parts = pick.rsplit(None, 1)
            if len(parts) == 2:
                tname = parts[0].lower().strip()
                if sel == tname:
                    matches.append((dec, o))
    if not matches:
        return None, None
    best = max(matches, key=lambda x: x[0])
    return best[0], best[1].get("bookmaker")


# ---------------------------------------------------------------------------
# Safe Zone builder
# ---------------------------------------------------------------------------

def _safe_zone_picks(best_market, best_pick, pred, home, away):
    """
    Return (balanced_pick, balanced_prob, banker_pick, banker_prob).
    All probs in %.  banker is None unless prob >= BANKER_THRESHOLD.
    """
    balanced_pick = balanced_prob = banker_pick = banker_prob = None

    if best_market == "moneyline":
        is_home = (best_pick.lower().strip() == home.lower().strip())
        if is_home:
            p15 = _num(pred.get("home_rl_plus15_prob"))
            p25 = _num(pred.get("home_rl_plus25_prob"))
            balanced_pick = f"{home} +1.5"
            balanced_prob = p15
            if p25 >= BANKER_THRESHOLD:
                banker_pick = f"{home} +2.5"
                banker_prob = p25
        else:
            p15 = _num(pred.get("away_rl_plus15_prob"))
            p25 = _num(pred.get("away_rl_plus25_prob"))
            balanced_pick = f"{away} +1.5"
            balanced_prob = p15
            if p25 >= BANKER_THRESHOLD:
                banker_pick = f"{away} +2.5"
                banker_prob = p25

    elif best_market == "totals":
        line = None
        for tok in best_pick.split():
            try:
                line = float(tok)
                break
            except ValueError:
                continue
        if line is not None:
            if "over" in best_pick.lower():
                bal_line = line - 1.0
                bnk_line = line - 2.0
                bal_prob = _total_prob(pred, "over", bal_line)
                balanced_pick = f"Over {bal_line:.1f}"
                balanced_prob = bal_prob
                bnk_prob = _total_prob(pred, "over", bnk_line)
                if bnk_prob >= BANKER_THRESHOLD:
                    banker_pick = f"Over {bnk_line:.1f}"
                    banker_prob = bnk_prob
            else:
                bal_line = line + 1.0
                bnk_line = line + 2.0
                bal_prob = _total_prob(pred, "under", bal_line)
                balanced_pick = f"Under {bal_line:.1f}"
                balanced_prob = bal_prob
                bnk_prob = _total_prob(pred, "under", bnk_line)
                if bnk_prob >= BANKER_THRESHOLD:
                    banker_pick = f"Under {bnk_line:.1f}"
                    banker_prob = bnk_prob

    elif best_market == "run_line":
        # Sharp is already a run-line pick; safe zone steps back to moneyline-equivalent
        is_home_fav = home.lower() in best_pick.lower()
        if is_home_fav:
            p = _num(pred.get("home_win_probability"))
            balanced_pick = f"{home} moneyline"
            balanced_prob = p
            if p >= BANKER_THRESHOLD:
                banker_pick = f"{home} +1.5"
                banker_prob = _num(pred.get("home_rl_plus15_prob"))
        else:
            p = _num(pred.get("away_win_probability"))
            balanced_pick = f"{away} moneyline"
            balanced_prob = p
            if p >= BANKER_THRESHOLD:
                banker_pick = f"{away} +1.5"
                banker_prob = _num(pred.get("away_rl_plus15_prob"))

    return balanced_pick, balanced_prob, banker_pick, banker_prob


def _total_prob(pred, side, line):
    """Interpolate over/under prob for an arbitrary line from stored 7.5/8.5/9.5."""
    mapping_over = {7.5: "over_75_probability", 8.5: "over_85_probability", 9.5: "over_95_probability"}
    mapping_under = {7.5: "under_75_probability", 8.5: "under_85_probability", 9.5: "under_95_probability"}
    mapping = mapping_over if side == "over" else mapping_under
    if line in mapping:
        return _num(pred.get(mapping[line]))
    # fall back to nearest stored line
    nearest = min(mapping.keys(), key=lambda k: abs(k - line))
    return _num(pred.get(mapping[nearest]))


def _safe_odds(odds_rows, pick):
    """Look up the best odds_decimal for a safe-zone pick (run-line or totals)."""
    if not pick:
        return None
    # Determine market type from the pick string
    if "+1.5" in pick or "+2.5" in pick or "-1.5" in pick:
        mkt = "run_line"
    elif "over" in pick.lower() or "under" in pick.lower():
        mkt = "totals"
    elif "moneyline" in pick.lower():
        team = pick.replace("moneyline", "").strip()
        dec, _ = _best_odds_decimal(odds_rows, "moneyline", team)
        return dec
    else:
        return None
    dec, _ = _best_odds_decimal(odds_rows, mkt, pick)
    return dec


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    preds = (
        supabase.table("mlb_run_predictions")
        .select("*")
        .eq("model_version", MODEL_VERSION)
        .order("created_at", desc=True)
        .limit(500)
        .execute()
        .data
    )

    seen = set()
    saved_fp = saved_sz = skipped = 0

    for pred in preds:
        gid = pred.get("game_id")
        if not gid or gid in seen:
            continue
        seen.add(gid)

        home = pred["home_team_name"]
        away = pred["away_team_name"]

        # Build candidates across all markets
        all_cands = (
            _ml_candidates(pred, home, away)
            + _totals_candidates(pred)
            + _runline_candidates(pred, home, away)
        )

        if not all_cands:
            skipped += 1
            continue

        # Sort by raw confidence descending; pick best and second-best
        all_cands.sort(key=lambda c: c["raw_confidence"], reverse=True)
        best = all_cands[0]
        second = all_cands[1] if len(all_cands) > 1 else None

        # Honest calibration
        cal_conf = _shrink(best["raw_confidence"])
        sec_cal = _shrink(second["raw_confidence"]) if second else None

        # No-vig edge vs real market
        odds_rows = _get_odds_rows(gid)
        novig_result = _resolve_novig(odds_rows, best["market"], best["pick"])

        if novig_result:
            novig_pct, pick_odds = novig_result
            edge = round(cal_conf - novig_pct, 2)
            flag = "REAL" if -10 <= edge <= 15 else "suspect"
            book_odds = pick_odds
        else:
            novig_pct = pick_odds = edge = None
            flag = "no-odds"
            book_odds, best_book = _best_odds_decimal(odds_rows, best["market"], best["pick"])
            book_odds = book_odds

        # American odds
        am_odds = None
        if book_odds and book_odds > 1:
            if book_odds >= 2:
                am_odds = int((book_odds - 1) * 100)
            else:
                am_odds = int(-100 / (book_odds - 1))

        # Upsert final prediction
        fp_row = {
            "game_id": gid,
            "home_team_name": home,
            "away_team_name": away,
            "best_pick": best["pick"],
            "market": best["market"],
            "raw_confidence": best["raw_confidence"],
            "calibrated_confidence": cal_conf,
            "bookmaker": None,
            "odds_decimal": book_odds,
            "odds_american": am_odds,
            "market_implied_probability": novig_pct,
            "model_edge": edge,
            "edge_flag": flag,
            "secondary_pick": second["pick"] if second else None,
            "secondary_market": second["market"] if second else None,
            "secondary_confidence": sec_cal,
            "updated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        }
        supabase.table("mlb_final_predictions").upsert(fp_row, on_conflict="game_id").execute()
        saved_fp += 1

        # Build Safe Zone
        bal_pick, bal_prob, bnk_pick, bnk_prob = _safe_zone_picks(
            best["market"], best["pick"], pred, home, away
        )
        bal_odds = _safe_odds(odds_rows, bal_pick)
        bnk_odds = _safe_odds(odds_rows, bnk_pick) if bnk_pick else None

        sz_row = {
            "game_id": gid,
            "home_team_name": home,
            "away_team_name": away,
            "sharp_pick": best["pick"],
            "sharp_market": best["market"],
            "sharp_edge": edge,
            "balanced_pick": bal_pick,
            "balanced_prob": round(bal_prob, 2) if bal_prob is not None else None,
            "balanced_odds_decimal": bal_odds,
            "banker_pick": bnk_pick,
            "banker_prob": round(bnk_prob, 2) if bnk_prob is not None else None,
            "banker_odds_decimal": bnk_odds,
            "updated_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        }
        supabase.table("mlb_safe_zone").upsert(sz_row, on_conflict="game_id").execute()
        saved_sz += 1

        sz_label = f"BANKER={bnk_pick}" if bnk_pick else f"balanced={bal_pick}"
        print(
            f"{home} vs {away} | SHARP: {best['pick']} ({best['market']}) "
            f"raw={best['raw_confidence']}% cal={cal_conf}% edge={edge}% [{flag}] | "
            f"SAFE: {sz_label}"
        )

    print(f"\n✅ MLB final picks: {saved_fp} | Safe Zones: {saved_sz} | skipped: {skipped}")


if __name__ == "__main__":
    main()
