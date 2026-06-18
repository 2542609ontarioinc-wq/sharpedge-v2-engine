from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_elite_score")
    .select("*")
    .order("elite_score", desc=True)
    .limit(20)
    .execute()
    .data
)

for r in rows:
    print(
        f'{r["home_team_name"]} vs {r["away_team_name"]} | '
        f'Pick: {r["pick"]} | '
        f'Elite: {r["elite_score"]} | '
        f'Tier: {r["elite_tier"]} | '
        f'Status: {r["publish_status"]}'
    )

    print("   Recommendation:", r.get("publish_recommendation"))

    failed = r.get("failed_gates") or []
    if failed:
        print("   Failed gates:")
        for g in failed:
            print(f'   - {g["gate"]}: {g["note"]}')

    print()