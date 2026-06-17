from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_master_picks")
    .select("*")
    .order("run_date", desc=True)
    .order("adjusted_elite_score", desc=True)
    .limit(10)
    .execute()
    .data
)

seen = set()

for r in rows:
    key = (r["game_id"], r["market"], r["pick"])
    if key in seen:
        continue
    seen.add(key)

    print(
        f'{r["home_team_name"]} vs {r["away_team_name"]} | '
        f'{r["pick"]} | '
        f'Status: {r["adaptive_publish_status"]} | '
        f'Elite: {r["elite_score"]} → {r["adjusted_elite_score"]} | '
        f'Grade: {r["grade"] or "PENDING"} | '
        f'Units: {r["units_result"] if r["units_result"] is not None else "-"}'
    )
