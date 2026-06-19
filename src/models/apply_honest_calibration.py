from datetime import datetime
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
SHRINK = 0.75


def num(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def shrink(raw):
    return round(50 + (raw - 50) * SHRINK, 2)


def pick_line(pick):
    """Extract the line number our model's pick refers to (default 2.5)."""
    for tok in pick.replace("/", " ").split():
        try:
            return float(tok)
        except Exception:
            continue
    return 2.5


def novig_implied(game_id, market, pick):
    """Return (novig_probability_pct, odds_decimal) or None if no matching odds."""
    rows = supabase.table("soccer_odds").select("*").eq("game_id", game_id).execute().data

    if market == "goals":
        line = pick_line(pick)
        side = "over" if "over" in pick.lower() else "under"
        # only the two legs of THIS exact line, from the same book
        legs = [o for o in rows
                if (o.get("market") or "").lower() == "totals"
                and num(o.get("line")) == line]
        if not legs:
            return None
        by_book = {}
        for o in legs:
            by_book.setdefault(o.get("bookmaker"), []).append(o)
        # find a book that has BOTH over and under for this line (true 2-way)
        for book, ol in by_book.items():
            sels = {(o.get("selection") or "").lower(): o for o in ol}
            if "over" in sels and "under" in sels:
                p_over = 1.0 / num(sels["over"]["odds_decimal"])
                p_under = 1.0 / num(sels["under"]["odds_decimal"])
                total = p_over + p_under
                if total <= 0:
                    continue
                mine = p_over if side == "over" else p_under
                pick_odds = num(sels[side]["odds_decimal"])
                return (round((mine / total) * 100, 2), pick_odds)
        return None

    if market == "winner":
        legs = [o for o in rows if (o.get("market") or "").lower() == "h2h"]
        if not legs:
            return None
        by_book = {}
        for o in legs:
            by_book.setdefault(o.get("bookmaker"), []).append(o)
        pick_lower = pick.lower().strip()
        for book, ol in by_book.items():
            # Rows within one bookmaker snapshot are inserted within milliseconds
            # of each other, so exact captured_at differs. Bucket by 10-second
            # windows to group them, then iterate newest→oldest.
            def _bucket(ts_str):
                try:
                    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    return dt.replace(second=(dt.second // 10) * 10, microsecond=0).isoformat()
                except Exception:
                    return ts_str or ""

            by_bucket = {}
            for o in ol:
                bkt = _bucket(o.get("captured_at") or "")
                by_bucket.setdefault(bkt, []).append(o)

            for bkt in sorted(by_bucket):  # oldest first = pre-match snapshot
                snap = by_bucket[bkt]
                by_sel = {}
                for o in snap:
                    sel = (o.get("selection") or "").strip()
                    odds_val = num(o.get("odds_decimal"))
                    if sel and odds_val > 1.0:
                        by_sel[sel] = odds_val
                if len(by_sel) != 3:
                    continue
                if "draw" not in {s.lower() for s in by_sel}:
                    continue
                total = sum(1.0 / v for v in by_sel.values())
                if total <= 0:
                    continue
                for sel, odds_val in by_sel.items():
                    if sel.lower() == pick_lower:
                        return (round((1.0 / odds_val / total) * 100, 2), odds_val)
        return None

    return None


def main():
    rows = supabase.table("final_soccer_predictions").select("*").execute().data
    updated = 0
    for r in rows:
        raw_conf = num(r.get("confidence"))
        cal_conf = shrink(raw_conf)
        market = r.get("market")
        result = novig_implied(r["game_id"], market, r.get("best_pick"))
        if result is not None:
            novig, pick_odds = result
            edge = round(cal_conf - novig, 2)
            flag = "REAL" if -10 <= edge <= 15 else "suspect"
        else:
            novig, pick_odds = None, None
            edge = None
            flag = "no-odds"
        update_payload = {
            "confidence": cal_conf,
            "model_edge": edge if edge is not None else r.get("model_edge"),
        }
        if pick_odds is not None:
            update_payload["odds_decimal"] = pick_odds
        supabase.table("final_soccer_predictions").update(
            update_payload
        ).eq("id", r["id"]).execute()
        updated += 1
        print(f'{r["home_team_name"]} vs {r["away_team_name"]} | {r["best_pick"]} | '
              f'conf {raw_conf}->{cal_conf}% | novig {novig}% | odds {pick_odds} | edge {edge}% [{flag}]')
    print(f"\n✅ Honest edges computed for {updated} picks.")


if __name__ == "__main__":
    main()
