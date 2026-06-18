import math
from collections import defaultdict
from statistics import mean
from datetime import datetime
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MAX_GOALS = 8
DC_RHO = -0.05
HOME_ADV = 1.10
GLOBAL = 1.35


def poisson(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def tau(i, j, l, m, r):
    if i == 0 and j == 0: return 1 - l * m * r
    if i == 0 and j == 1: return 1 + l * r
    if i == 1 and j == 0: return 1 + m * r
    if i == 1 and j == 1: return 1 - r
    return 1.0


def matrix(h, a):
    M = [[poisson(i, h) * poisson(j, a) * tau(i, j, h, a, DC_RHO)
          for j in range(MAX_GOALS + 1)] for i in range(MAX_GOALS + 1)]
    t = sum(sum(row) for row in M)
    return [[c / t for c in row] for row in M]


def probs(h, a):
    M = matrix(h, a)
    hw = dr = aw = btts = o25 = 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = M[i][j]
            if i > j: hw += p
            elif i == j: dr += p
            else: aw += p
            if i > 0 and j > 0: btts += p
            if i + j > 2.5: o25 += p
    return hw, dr, aw, btts, o25


def main():
    rows = (supabase.table("soccer_team_stat_history").select("*")
            .order("game_date").limit(10000).execute().data)

    # group each team's matches chronologically
    by_team = defaultdict(list)
    for r in rows:
        if r.get("game_date"):
            by_team[r["team_name"]].append(r)
    for t in by_team:
        by_team[t].sort(key=lambda x: x["game_date"])

    # collect distinct fixtures (two team-rows each)
    fixtures = defaultdict(dict)
    for r in rows:
        fixtures[r["fixture_id"]][("home" if r.get("is_home") else "away")] = r

    def strength_before(team, date):
        past = [m for m in by_team.get(team, []) if m["game_date"] < date]
        if len(past) < 2:
            return None
        recent = past[-10:]
        gf = mean([float(m.get("goals_for") or 0) for m in recent])
        ga = mean([float(m.get("goals_against") or 0) for m in recent])
        return gf / GLOBAL, ga / GLOBAL

    win_hit = win_tot = 0
    o25_buckets = defaultdict(lambda: [0, 0])   # bucket -> [hits, total]
    btts_buckets = defaultdict(lambda: [0, 0])
    o25_pred_hit = o25_pred_tot = 0
    tested = 0

    for fid, sides in fixtures.items():
        if "home" not in sides or "away" not in sides:
            continue
        h, a = sides["home"], sides["away"]
        date = h["game_date"]
        hs = strength_before(h["team_name"], date)
        as_ = strength_before(a["team_name"], date)
        if not hs or not as_:
            continue

        h_att, h_def = hs
        a_att, a_def = as_
        home_xg = max(0.2, min(4.5, GLOBAL * h_att * a_def * HOME_ADV))
        away_xg = max(0.2, min(4.5, GLOBAL * a_att * h_def))

        hw, dr, aw, btts_p, o25_p = probs(home_xg, away_xg)

        # actual
        hg = int(h.get("goals_for") or 0)
        ag = int(a.get("goals_for") or 0)
        actual_winner = "home" if hg > ag else "away" if ag > hg else "draw"
        actual_o25 = (hg + ag) > 2.5
        actual_btts = hg > 0 and ag > 0

        # winner accuracy
        pred = max([("home", hw), ("draw", dr), ("away", aw)], key=lambda x: x[1])[0]
        win_tot += 1
        if pred == actual_winner:
            win_hit += 1

        # over 2.5 directional accuracy (model picks over if >=50%)
        if o25_p >= 0.5:
            o25_pred_tot += 1
            if actual_o25:
                o25_pred_hit += 1

        # calibration buckets
        b = int(o25_p * 10) * 10
        o25_buckets[b][1] += 1
        if actual_o25:
            o25_buckets[b][0] += 1
        bb = int(btts_p * 10) * 10
        btts_buckets[bb][1] += 1
        if actual_btts:
            btts_buckets[bb][0] += 1

        tested += 1

    print(f"\n===== BACKTEST (point-in-time, out-of-sample) =====")
    print(f"Matches tested: {tested}")
    print(f"\nWINNER accuracy: {round(win_hit/win_tot*100,1) if win_tot else 0}% ({win_hit}/{win_tot})")
    print(f"OVER 2.5 directional hit rate (model picked Over): "
          f"{round(o25_pred_hit/o25_pred_tot*100,1) if o25_pred_tot else 0}% ({o25_pred_hit}/{o25_pred_tot})")

    print(f"\n--- OVER 2.5 CALIBRATION (did predicted % match reality?) ---")
    for b in sorted(o25_buckets):
        hits, tot = o25_buckets[b]
        if tot:
            print(f"  model said {b}-{b+9}%: actually hit {round(hits/tot*100,1)}% ({tot} games)")

    print(f"\n--- BTTS CALIBRATION ---")
    for b in sorted(btts_buckets):
        hits, tot = btts_buckets[b]
        if tot:
            print(f"  model said {b}-{b+9}%: actually hit {round(hits/tot*100,1)}% ({tot} games)")

    print(f"\nNote: point-in-time test on real history. Small sample — treat as directional.")


if __name__ == "__main__":
    main()
