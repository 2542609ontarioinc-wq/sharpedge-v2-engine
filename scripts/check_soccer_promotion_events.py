from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

events = (
    supabase.table("soccer_pick_status_events")
    .select("*")
    .order("created_at", desc=True)
    .limit(20)
    .execute()
    .data
)

current = (
    supabase.table("soccer_pick_current_status")
    .select("*")
    .order("elite_score", desc=True)
    .limit(20)
    .execute()
    .data
)

print("=== CURRENT PICK STATUS ===")
for r in current:
    print(
        f'{r["home_team_name"]} vs {r["away_team_name"]} | '
        f'{r["pick"]} | {r["publish_status"]} | '
        f'Elite: {r["elite_score"]}'
    )

print("\n=== RECENT PROMOTION EVENTS ===")
if not events:
    print("No promotion/demotion events yet.")
else:
    for e in events:
        print(e["message"])