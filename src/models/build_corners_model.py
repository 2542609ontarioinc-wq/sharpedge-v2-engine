import math
from collections import defaultdict
from statistics import mean
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

GLOBAL_AVG_CORNERS_PER_TEAM = 4.5  # typical ~9 total per game
HOME_CORNER_ADV = 1.05             # home teams earn slightly more corners
SHRINK_K = 5
HISTORY_WINDOW = 10


def safe(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def poisson_pmf(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def poisson_over(line, lam):
    """P(X > line) for integer-valued Poisson(lam)."""
    k_max = int(math.floor(line))
    p_under = sum(poisson_pmf(k, lam) for k in range(k_max + 1))
    return max(0.0, min(1.0, 1.0 - p_under))


def shrink(raw_pct):
    """Honest shrink toward 50: reduces overconfidence in uncalibrated markets."""
    return 50.0 + (raw_pct - 50.0) * 0.75


def build_team_corner_rates():
    rows = (
        supabase.table("soccer_team_stat_history")
        .select("team_name, game_date, corners")
        .order("game_date", desc=True)
        .limit(20000)
        .execute()
        .data
    )

    by_team = defaultdict(list)
    for r in rows:
        by_team[r["team_name"]].append(r)

    rates = {}
    for team, matches in by_team.items():
        recent = sorted(matches, key=lambda x: x.get("game_date") or "", reverse=True)[:HISTORY_WINDOW]
        n = len(recent)
        corners_per_game = [safe(m.get("corners")) for m in recent]
        team_avg = mean(corners_per_game) if corners_per_game else GLOBAL_AVG_CORNERS_PER_TEAM
        w = n / (n + SHRINK_K)
        rate = w * team_avg + (1 - w) * GLOBAL_AVG_CORNERS_PER_TEAM
        rates[team] = {"rate": round(max(1.0, rate), 3), "games": n}
    return rates


def main():
    rates = build_team_corner_rates()
    print(f"Team corner rates estimated: {len(rates)}")

    games = (
        supabase.table("soccer_match_strength")
        .select("*")
        .order("created_at", desc=True)
        .limit(200)
        .execute()
        .data
    )

    seen = set()
    saved = 0

    for g in games:
        gid = g["game_id"]
        if gid in seen:
            continue
        seen.add(gid)

        home = g["home_team_name"]
        away = g["away_team_name"]
        hr = rates.get(home, {"rate": GLOBAL_AVG_CORNERS_PER_TEAM})["rate"] * HOME_CORNER_ADV
        ar = rates.get(away, {"rate": GLOBAL_AVG_CORNERS_PER_TEAM})["rate"]
        total_lambda = hr + ar

        over85 = round(shrink(poisson_over(8.5, total_lambda) * 100), 2)
        over95 = round(shrink(poisson_over(9.5, total_lambda) * 100), 2)
        over105 = round(shrink(poisson_over(10.5, total_lambda) * 100), 2)

        row = {
            "game_id": gid,
            "model_version": "corners_v1",
            "home_team_name": home,
            "away_team_name": away,
            "expected_home_corners": round(hr, 2),
            "expected_away_corners": round(ar, 2),
            "expected_total_corners": round(total_lambda, 2),
            "over_85_probability": over85,
            "over_95_probability": over95,
            "over_105_probability": over105,
            "under_95_probability": round(100.0 - over95, 2),
            "pick_label": "PROJECTION",
        }

        supabase.table("soccer_corners_prediction_versions").insert(row).execute()
        saved += 1
        print(
            f"{home} vs {away} | xCorners H={hr:.1f} A={ar:.1f} Tot={total_lambda:.1f} | "
            f"O8.5={over85:.1f}% O9.5={over95:.1f}% O10.5={over105:.1f}% [PROJECTION]"
        )

    print(f"\n✅ Corners prediction rows saved: {saved}")


if __name__ == "__main__":
    main()
