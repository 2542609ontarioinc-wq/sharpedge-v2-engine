"""
Build mlb_prop_detail: enriched per-prop diagnostic row for every graded prop pick.

Joins:
  mlb_prop_grades     — grade, actual value, units
  mlb_player_props    — model_projection, calibrated_over_prob, model_edge, edge_flag

DIAGNOSTIC ONLY — does not touch any prediction or pick table.
Run after grade_mlb_prop_picks.
"""
from datetime import datetime, timezone

from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def _num(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def main():
    grades = supabase.table("mlb_prop_grades").select("*").execute().data

    # Prop predictions keyed by (game_id, player_mlb_id, prop_market)
    props_raw = (
        supabase.table("mlb_player_props")
        .select(
            "game_id,player_mlb_id,prop_market,"
            "model_projection,calibrated_over_prob,model_edge,edge_flag"
        )
        .execute()
        .data
    )
    props_map = {
        (p["game_id"], p["player_mlb_id"], p["prop_market"]): p
        for p in props_raw
    }

    now = datetime.now(timezone.utc).isoformat()
    saved = 0

    for gr in grades:
        gid = gr.get("game_id")
        pid = gr.get("player_mlb_id")
        mkt = gr.get("prop_market")
        if not all([gid, pid, mkt]):
            continue

        prop = props_map.get((gid, pid, mkt)) or {}

        model_proj = _num(prop.get("model_projection"))
        actual     = _num(gr.get("actual_value"))
        prop_bias  = (
            round(model_proj - actual, 3)
            if model_proj is not None and actual is not None
            else None
        )

        row = {
            "game_id":          gid,
            "game_date":        gr.get("game_date"),
            "player_name":      gr.get("player_name"),
            "player_mlb_id":    pid,
            "player_type":      gr.get("player_type"),
            "prop_market":      mkt,
            "market_line":      _num(gr.get("market_line")),
            "pick_side":        gr.get("pick_side"),
            "model_projection": model_proj,
            "calibrated_prob":  _num(prop.get("calibrated_over_prob")),
            "model_edge":       _num(prop.get("model_edge")),
            "best_odds_decimal":_num(gr.get("best_odds_decimal")),
            "edge_flag":        prop.get("edge_flag") or gr.get("edge_flag"),
            "actual_value":     actual,
            "prop_bias":        prop_bias,
            "grade":            gr.get("grade"),
            "units_result":     _num(gr.get("units_result")),
            "graded_at":        gr.get("graded_at") or now,
        }

        supabase.table("mlb_prop_detail").upsert(
            row, on_conflict="game_id,player_mlb_id,prop_market"
        ).execute()
        saved += 1

    print(f"✅ MLB prop detail built: {saved} rows")


if __name__ == "__main__":
    main()
