from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def load_map():
    rows = supabase.table("soccer_calibration_map").select("*").execute().data
    m = {}
    for r in rows:
        m.setdefault(r["market"], {})[int(r["bucket_low"])] = float(r["actual_rate"])
    return m


def calibrate(cal_map, market, raw_prob):
    """raw_prob is 0-100. Map to real hit-rate via its bucket."""
    table = cal_map.get(market)
    if not table:
        return raw_prob
    bucket = int(raw_prob // 10) * 10
    bucket = max(0, min(90, bucket))
    return table.get(bucket, raw_prob)


def main():
    cal = load_map()
    print("Calibration markets loaded:", list(cal.keys()))

    rows = (
        supabase.table("final_soccer_predictions")
        .select("*")
        .execute()
        .data
    )

    updated = 0
    for r in rows:
        market = r.get("market")
        # map our market names to calibration market names
        if market == "goals":
            cal_market = "over_25"
        elif market == "winner":
            cal_market = "winner"
        elif market == "btts":
            cal_market = "btts"
        else:
            cal_market = None

        raw_conf = float(r.get("confidence") or 0)
        cal_conf = calibrate(cal, cal_market, raw_conf) if cal_market else raw_conf

        # recompute honest edge vs the book using CALIBRATED prob
        implied = float(r.get("market_implied_probability") or 0)
        honest_edge = round(cal_conf - implied, 2) if implied else None

        supabase.table("final_soccer_predictions").update({
            "confidence": round(cal_conf, 2),
            "model_edge": honest_edge if honest_edge is not None else r.get("model_edge"),
        }).eq("id", r["id"]).execute()

        updated += 1
        print(
            f'{r["home_team_name"]} vs {r["away_team_name"]} | {r["best_pick"]} | '
            f'raw {raw_conf}% -> calibrated {round(cal_conf,1)}% | '
            f'honest edge {honest_edge}%'
        )

    print(f"\n✅ Calibration applied to {updated} picks. Displayed % and edges are now truth-corrected.")


if __name__ == "__main__":
    main()
