from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_adaptive_prediction_adjustments_v1")
    .select("*")
    .order("adjusted_elite_score", desc=True)
    .limit(20)
    .execute()
    .data
)

for r in rows:
    print(
        f'{r["home_team_name"]} vs {r["away_team_name"]} | '
        f'{r["pick"]} | '
        f'Elite {r["original_elite_score"]} → {r["adjusted_elite_score"]} | '
        f'Adj {r["adjustment_total"]}% | '
        f'{r["publish_status"]} → {r["adaptive_publish_status"]}'
    )
