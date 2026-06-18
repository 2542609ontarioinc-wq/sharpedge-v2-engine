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
                return round((mine / total) * 100, 2)
        return None

    if market == "winner":
        legs = [o for o in rows if (o.get("market") or "").lower() == "h2h"]
        if not legs:
            return None
        by_book = {}
        for o in legs:
            by_book.setdefault(o.get("bookmaker"), []).append(o)
        # need all 3 (home/draw/away) for a true no-vig
        for book, ol in by_book.items():
            if len(ol) >= 3:
                total = sum(1.0 / num(o["odds_decimal"]) for o in ol if num(o["odds_decimal"]) > 0)
                for o in ol:
                    if (o.get("selection") or "").lower() == pick.lower():
                        mine = 1.0 / num(o["odds_decimal"])
                        return round((mine / total) * 100, 2)
        return None

    return None


def main():
    rows = supabase.table("final_soccer_predictions").select("*").execute().data
    updated = 0
    for r in rows:
        raw_conf = num(r.get("confidence"))
        cal_conf = shrink(raw_conf)
        market = r.get("market")
        novig = novig_implied(r["game_id"], market, r.get("best_pick"))
        if novig is not None:
            edge = round(cal_conf - novig, 2)
            flag = "REAL" if -10 <= edge <= 15 else "suspect"
        else:
            edge = None
            flag = "no-odds"
        supabase.table("final_soccer_predictions").update({
            "confidence": cal_conf,
            "model_edge": edge if edge is not None else r.get("model_edge"),
        }).eq("id", r["id"]).execute()
        updated += 1
        print(f'{r["home_team_name"]} vs {r["away_team_name"]} | {r["best_pick"]} | '
              f'conf {raw_conf}->{cal_conf}% | novig {novig}% | edge {edge}% [{flag}]')
    print(f"\n✅ Honest edges computed for {updated} picks.")


if __name__ == "__main__":
    main()
