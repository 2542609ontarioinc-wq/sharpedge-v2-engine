from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
OBJECTS = ["soccer_market_value","soccer_safety_engine_v2","soccer_safety_engine_v3","soccer_elite_score","soccer_live_lineups","soccer_live_odds_snapshots","soccer_closing_line_value","soccer_pick_grades_v2","soccer_pick_current_status","soccer_pick_status_events","soccer_master_picks","soccer_adaptive_weights_v1","soccer_adaptive_prediction_adjustments_v1","soccer_analytics_feedback_v1","final_pro_soccer_pick_history","soccer_api_ready_view","soccer_today_watchlist_view","soccer_master_today_view","soccer_pick_dashboard_view"]
print("CHECK")
print("-----")
missing=[]
for o in OBJECTS:
    try:
        supabase.table(o).select("*").limit(1).execute()
        print("EXISTS  ", o)
    except Exception as e:
        print("MISSING ", o)
        missing.append(o)
print("\nMISSING COUNT:", len(missing))
