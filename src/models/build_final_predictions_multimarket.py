from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def num(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def best_odds_for(game_id, market, pick):
    rows = (supabase.table("soccer_odds").select("*").eq("game_id", game_id)
            .order("odds_decimal", desc=True).execute().data)
    matches = []
    for o in rows:
        omkt = (o.get("market") or "").lower()
        osel = (o.get("selection") or "").lower()
        if market == "winner" and omkt == "h2h" and pick.lower() == osel:
            matches.append(o)
        elif market == "goals" and omkt == "totals":
            target = "over" if "over" in pick.lower() else "under"
            if osel == target:
                matches.append(o)
        elif market == "btts" and omkt in ("btts", "both_teams_to_score"):
            yn = "yes" if "yes" in pick.lower() else "no"
            if yn in osel:
                matches.append(o)
    if not matches:
        return None
    return sorted(matches, key=lambda x: num(x.get("odds_decimal")), reverse=True)[0]


def candidate(game_id, market, pick, conf):
    if not pick:
        return None
    odds = best_odds_for(game_id, market, pick)
    if not odds:
        return None
    model_prob = num(conf) / 100.0
    dec = num(odds["odds_decimal"])
    implied = 1.0 / dec if dec > 0 else 0
    return {"market": market, "pick": pick, "confidence": round(num(conf), 2),
            "bookmaker": odds.get("bookmaker"), "odds_decimal": odds.get("odds_decimal"),
            "odds_american": odds.get("odds_american"),
            "market_implied_probability": round(implied * 100, 2),
            "model_edge": round((model_prob - implied) * 100, 2)}


def latest_goals(game_id):
    rows = (supabase.table("soccer_goals_prediction_versions").select("*")
            .eq("game_id", game_id).order("created_at", desc=True).limit(1).execute().data)
    return rows[0] if rows else {}


def latest_winner(game_id):
    rows = (supabase.table("soccer_prediction_versions").select("*")
            .eq("game_id", game_id).order("created_at", desc=True).limit(1).execute().data)
    return rows[0] if rows else {}


def build_safe_zone(game_id, home, away, best):
    g = latest_goals(game_id)
    w = latest_winner(game_id)
    balanced_pick = banker_pick = None
    balanced_prob = banker_prob = None

    if best["market"] == "goals" and "over" in best["pick"].lower():
        o15 = num(g.get("over_15_probability"))
        balanced_pick, balanced_prob = "Over 1.5", o15
        if o15 >= 80:
            banker_pick, banker_prob = "Over 1.5", o15
    elif best["market"] == "goals" and "under" in best["pick"].lower():
        u35 = round(100 - num(g.get("over_35_probability")), 2)
        balanced_pick, balanced_prob = "Under 3.5", u35
        if u35 >= 80:
            banker_pick, banker_prob = "Under 3.5", u35
    elif best["market"] == "winner":
        hp, dp, ap = num(w.get("home_probability")), num(w.get("draw_probability")), num(w.get("away_probability"))
        if best["pick"] == home:
            dc = round(hp + dp, 2); balanced_pick = f"{home} or Draw"
        elif best["pick"] == away:
            dc = round(ap + dp, 2); balanced_pick = f"{away} or Draw"
        else:
            dc = round(max(hp, ap) + dp, 2); balanced_pick = "Double Chance"
        balanced_prob = dc
        if dc >= 80:
            banker_pick, banker_prob = balanced_pick, dc
    else:
        balanced_pick, balanced_prob = best["pick"], best["confidence"]

    supabase.table("soccer_safe_zone").upsert({
        "game_id": game_id, "home_team_name": home, "away_team_name": away,
        "sharp_pick": best["pick"], "sharp_market": best["market"], "sharp_edge": best["model_edge"],
        "balanced_pick": balanced_pick, "balanced_prob": balanced_prob,
        "banker_pick": banker_pick, "banker_prob": banker_prob,
    }, on_conflict="game_id").execute()


def main():
    ens = (supabase.table("soccer_ensemble_predictions").select("*")
           .order("created_at", desc=True).limit(500).execute().data)
    seen = set(); saved = skipped = 0
    for r in ens:
        gid = r["game_id"]
        if gid in seen:
            continue
        seen.add(gid)
        cands = [c for c in (
            candidate(gid, "winner", r.get("winner_pick"), r.get("winner_confidence")),
            candidate(gid, "goals", r.get("goals_pick"), r.get("goals_confidence")),
            candidate(gid, "btts", r.get("btts_pick"), r.get("btts_confidence")),
        ) if c]
        if not cands:
            skipped += 1
            continue
        cands.sort(key=lambda x: x["model_edge"], reverse=True)
        best = cands[0]; second = cands[1] if len(cands) > 1 else None
        supabase.table("final_soccer_predictions").upsert({
            "game_id": gid, "home_team_name": r["home_team_name"], "away_team_name": r["away_team_name"],
            "best_pick": best["pick"], "market": best["market"], "confidence": best["confidence"],
            "secondary_pick": second["pick"] if second else None,
            "secondary_market": second["market"] if second else None,
            "secondary_confidence": second["confidence"] if second else None,
            "value_rating": r.get("value_rating"), "ensemble_score": r.get("ensemble_score"),
            "bookmaker": best["bookmaker"], "odds_decimal": best["odds_decimal"],
            "odds_american": best["odds_american"],
            "market_implied_probability": best["market_implied_probability"], "model_edge": best["model_edge"],
        }, on_conflict="game_id,market").execute()
        build_safe_zone(gid, r["home_team_name"], r["away_team_name"], best)
        saved += 1
        sz = "BANKER" if best["model_edge"] else ""
        print(f'{r["home_team_name"]} vs {r["away_team_name"]} | SHARP: {best["pick"]} ({best["market"]}) edge {best["model_edge"]}%')
    print(f"\n✅ Sharp picks + Safe Zone saved: {saved} | skipped (no odds): {skipped}")


if __name__ == "__main__":
    main()
