import math
from collections import defaultdict
from statistics import mean
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

MAX_GOALS = 8
SHRINK_K = 5
HOME_ADV = 1.10
DC_RHO = -0.05
GLOBAL_AVG_GOALS = 1.35


def safe(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def build_team_strengths():
    history = supabase.table("soccer_team_stat_history").select("*").limit(10000).execute().data
    baselines = supabase.table("soccer_league_baselines").select("*").execute().data
    base_by_league = {str(b["league_id"]): b for b in baselines}
    priors = supabase.table("soccer_team_global_priors").select("*").execute().data
    prior_by_team = {p["team_name"]: p for p in priors}

    by_team = defaultdict(list)
    for row in history:
        by_team[row["team_name"]].append(row)

    # Include teams that only exist in priors (e.g. national teams with
    # no club stat-history). Without this they fell back to flat 1.0/1.0.
    for team in prior_by_team:
        if team not in by_team:
            by_team[team] = []

    strengths = {}
    for team, matches in by_team.items():
        n = len(matches)
        gf = mean([safe(m.get("goals_for")) for m in matches]) if matches else None
        ga = mean([safe(m.get("goals_against")) for m in matches]) if matches else None
        league_id = str(matches[0].get("league_id")) if matches else None
        base = base_by_league.get(league_id)
        league_team_goals = safe(base.get("avg_goals")) / 2 if base and safe(base.get("avg_goals")) else GLOBAL_AVG_GOALS
        if league_team_goals <= 0:
            league_team_goals = GLOBAL_AVG_GOALS
        prior = prior_by_team.get(team)
        if gf is None or ga is None:
            pa = safe(prior.get("prior_attack_index"), 100) / 100.0 if prior else 1.0
            pd = safe(prior.get("prior_defense_index"), 50) / 50.0 if prior else 1.0
            raw_attack, raw_defense = pa, pd
        else:
            raw_attack = gf / league_team_goals if league_team_goals else 1.0
            raw_defense = ga / league_team_goals if league_team_goals else 1.0
        if prior:
            prior_attack = safe(prior.get("prior_attack_index"), 100) / 100.0
            prior_defense = safe(prior.get("prior_defense_index"), 50) / 50.0
        else:
            prior_attack = 1.0
            prior_defense = 1.0
        w = n / (n + SHRINK_K)
        attack = max(0.4, min(2.2, w * raw_attack + (1 - w) * prior_attack))
        defense = max(0.4, min(2.2, w * raw_defense + (1 - w) * prior_defense))
        strengths[team] = {"attack": round(attack, 3), "defense": round(defense, 3),
                           "games": n, "league_team_goals": round(league_team_goals, 3)}
    return strengths


def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def dc_tau(i, j, lam, mu, rho):
    if i == 0 and j == 0: return 1 - (lam * mu * rho)
    if i == 0 and j == 1: return 1 + (lam * rho)
    if i == 1 and j == 0: return 1 + (mu * rho)
    if i == 1 and j == 1: return 1 - rho
    return 1.0


def score_matrix(home_xg, away_xg):
    matrix = [[0.0] * (MAX_GOALS + 1) for _ in range(MAX_GOALS + 1)]
    total = 0.0
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = poisson_pmf(i, home_xg) * poisson_pmf(j, away_xg) * dc_tau(i, j, home_xg, away_xg, DC_RHO)
            p = max(p, 0.0)
            matrix[i][j] = p
            total += p
    if total > 0:
        for i in range(MAX_GOALS + 1):
            for j in range(MAX_GOALS + 1):
                matrix[i][j] /= total
    return matrix


def markets_from_matrix(matrix):
    home_win = draw = away_win = btts_yes = exp_home = exp_away = 0.0
    over = {1.5: 0.0, 2.5: 0.0, 3.5: 0.0, 4.5: 0.0}
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            p = matrix[i][j]
            if p <= 0: continue
            tg = i + j
            if i > j: home_win += p
            elif i == j: draw += p
            else: away_win += p
            if i > 0 and j > 0: btts_yes += p
            for line in over:
                if tg > line: over[line] += p
            exp_home += i * p
            exp_away += j * p
    return {"home_win": round(home_win*100,2), "draw": round(draw*100,2), "away_win": round(away_win*100,2),
            "btts_yes": round(btts_yes*100,2), "btts_no": round((1-btts_yes)*100,2),
            "over_15": round(over[1.5]*100,2), "over_25": round(over[2.5]*100,2),
            "over_35": round(over[3.5]*100,2), "over_45": round(over[4.5]*100,2),
            "under_25": round((1-over[2.5])*100,2), "exp_home": round(exp_home,2), "exp_away": round(exp_away,2)}


def main():
    strengths = build_team_strengths()
    print(f"Team strengths estimated: {len(strengths)}")
    games = supabase.table("soccer_match_strength").select("*").order("created_at", desc=True).limit(200).execute().data
    seen = set()
    saved_goals = saved_winner = 0
    for g in games:
        gid = g["game_id"]
        if gid in seen: continue
        seen.add(gid)
        home = g["home_team_name"]; away = g["away_team_name"]
        hs = strengths.get(home); as_ = strengths.get(away)
        league_goals = hs["league_team_goals"] if hs else GLOBAL_AVG_GOALS
        h_attack = hs["attack"] if hs else 1.0
        h_defense = hs["defense"] if hs else 1.0
        a_attack = as_["attack"] if as_ else 1.0
        a_defense = as_["defense"] if as_ else 1.0
        home_xg = max(0.2, min(4.5, league_goals * h_attack * a_defense * HOME_ADV))
        away_xg = max(0.2, min(4.5, league_goals * a_attack * h_defense))
        m = markets_from_matrix(score_matrix(home_xg, away_xg))
        goals_row = {"game_id": gid, "model_version": "goals_dc_v3", "home_team_name": home, "away_team_name": away,
                     "expected_home_goals": m["exp_home"], "expected_away_goals": m["exp_away"],
                     "expected_total_goals": round(m["exp_home"]+m["exp_away"],2),
                     "over_15_probability": m["over_15"], "over_25_probability": m["over_25"],
                     "over_35_probability": m["over_35"], "under_25_probability": m["under_25"],
                     "btts_yes_probability": m["btts_yes"], "btts_no_probability": m["btts_no"]}
        supabase.table("soccer_goals_prediction_versions").insert(goals_row).execute()
        saved_goals += 1
        if m["home_win"] >= m["away_win"] and m["home_win"] >= m["draw"]:
            winner, conf = home, m["home_win"]
        elif m["away_win"] >= m["home_win"] and m["away_win"] >= m["draw"]:
            winner, conf = away, m["away_win"]
        else:
            winner, conf = "Draw", m["draw"]
        winner_row = {"game_id": gid, "model_version": "winner_dc_v3", "home_team_name": home, "away_team_name": away,
                      "home_probability": m["home_win"], "draw_probability": m["draw"], "away_probability": m["away_win"],
                      "predicted_winner": winner, "confidence_score": conf,
                      "form_difference": safe(g.get("form_difference")),
                      "goal_difference_edge": round(m["exp_home"]-m["exp_away"],2), "home_advantage_score": 5}
        supabase.table("soccer_prediction_versions").insert(winner_row).execute()
        saved_winner += 1
        print(f"{home} vs {away} | xG {home_xg:.2f}-{away_xg:.2f} | 1X2 {m['home_win']}/{m['draw']}/{m['away_win']} | O2.5 {m['over_25']} | BTTS {m['btts_yes']}")
    print(f"\n✅ DC goals rows: {saved_goals} | DC winner rows: {saved_winner}")


if __name__ == "__main__":
    main()
