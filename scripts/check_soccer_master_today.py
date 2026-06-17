from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

s = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    s.table("soccer_master_today_view")
    .select("*")
    .execute()
    .data
)

print("Today dashboard picks:", len(rows))
for r in rows:
    print(
        f'{r["home_team_name"]} vs {r["away_team_name"]} | '
        f'{r["pick"]} | '
        f'{r["adaptive_publish_status"]} | '
        f'Elite: {r["adjusted_elite_score"]} | '
        f'Grade: {r["grade"] or "PENDING"}'
    )
