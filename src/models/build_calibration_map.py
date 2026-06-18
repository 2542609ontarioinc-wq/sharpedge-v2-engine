import math
from collections import defaultdict
from statistics import mean
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
MAX_GOALS = 8; DC_RHO = -0.05; HOME_ADV = 1.10; GLOBAL = 1.35


def poisson(k, l): return math.exp(-l) * (l ** k) / math.factorial(k)
def tau(i, j, l, m, r):
    if i == 0 and j == 0: return 1 - l*m*r
    if i == 0 and j == 1: return 1 + l*r
    if i == 1 and j == 0: return 1 + m*r
    if i == 1 and j == 1: return 1 - r
    return 1.0
def mat(h, a):
    M = [[poisson(i, h)*poisson(j, a)*tau(i, j, h, a, DC_RHO) for j in range(MAX_GOALS+1)] for i in range(MAX_GOALS+1)]
    t = sum(sum(r) for r in M); return [[c/t for c in r] for r in M]
def probs(h, a):
    M = mat(h, a); hw=dr=aw=btts=o25=0.0
    for i in range(MAX_GOALS+1):
        for j in range(MAX_GOALS+1):
            p=M[i][j]
            if i>j: hw+=p
            elif i==j: dr+=p
            else: aw+=p
            if i>0 and j>0: btts+=p
            if i+j>2.5: o25+=p
    return hw, dr, aw, btts, o25


def monotonic(buckets):
    # force actual_rate non-decreasing across buckets (isotonic-lite)
    keys = sorted(buckets)
    out = {}; last = 0.0
    for k in keys:
        hits, tot = buckets[k]
        rate = (hits/tot) if tot else last
        rate = max(rate, last)   # never go down
        out[k] = (round(rate*100, 1), tot)
        last = rate
    return out


def main():
    rows = (supabase.table("soccer_team_stat_history").select("*").order("game_date").limit(10000).execute().data)
    by_team = defaultdict(list)
    for r in rows:
        if r.get("game_date"): by_team[r["team_name"]].append(r)
    for t in by_team: by_team[t].sort(key=lambda x: x["game_date"])
    fixtures = defaultdict(dict)
    for r in rows:
        fixtures[r["fixture_id"]][("home" if r.get("is_home") else "away")] = r

    def sb(team, date):
        past = [m for m in by_team.get(team, []) if m["game_date"] < date]
        if len(past) < 2: return None
        rec = past[-10:]
        return mean([float(m.get("goals_for") or 0) for m in rec])/GLOBAL, mean([float(m.get("goals_against") or 0) for m in rec])/GLOBAL

    o25_b = defaultdict(lambda: [0, 0]); btts_b = defaultdict(lambda: [0, 0]); win_b = defaultdict(lambda: [0, 0])

    for fid, s in fixtures.items():
        if "home" not in s or "away" not in s: continue
        h, a = s["home"], s["away"]; date = h["game_date"]
        hs = sb(h["team_name"], date); as_ = sb(a["team_name"], date)
        if not hs or not as_: continue
        hxg = max(0.2, min(4.5, GLOBAL*hs[0]*as_[1]*HOME_ADV))
        axg = max(0.2, min(4.5, GLOBAL*as_[0]*hs[1]))
        hw, dr, aw, btts_p, o25_p = probs(hxg, axg)
        hg = int(h.get("goals_for") or 0); ag = int(a.get("goals_for") or 0)
        # over 2.5
        b = int(o25_p*10)*10; o25_b[b][1] += 1
        if (hg+ag) > 2.5: o25_b[b][0] += 1
        # btts
        bb = int(btts_p*10)*10; btts_b[bb][1] += 1
        if hg > 0 and ag > 0: btts_b[bb][0] += 1
        # winner (use max prob bucket)
        wp = max(hw, dr, aw); wb = int(wp*10)*10; win_b[wb][1] += 1
        pred = "home" if hw == wp else "away" if aw == wp else "draw"
        actual = "home" if hg > ag else "away" if ag > hg else "draw"
        if pred == actual: win_b[wb][0] += 1

    def store(market, buckets):
        total = sum(t for _, t in buckets.values())
        flag = "LOW_CONFIDENCE" if total < 30 else "OK"
        cal = monotonic(buckets)
        for b, (rate, tot) in cal.items():
            # blend with raw midpoint if low confidence
            mid = b + 5
            final = rate if flag == "OK" else round((rate + mid)/2, 1)
            supabase.table("soccer_calibration_map").upsert({
                "market": market, "bucket_low": b, "predicted_mid": mid,
                "actual_rate": final, "sample": tot, "confidence_flag": flag,
            }, on_conflict="market,bucket_low").execute()
        print(f"{market}: stored {len(cal)} buckets | total {total} | {flag}")

    store("over_25", o25_b)
    store("btts", btts_b)
    store("winner", win_b)
    print("\n✅ Calibration map built. Displayed % now mapped to real hit-rate.")


if __name__ == "__main__":
    main()
