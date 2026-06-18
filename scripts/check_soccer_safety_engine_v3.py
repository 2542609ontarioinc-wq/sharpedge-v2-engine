from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_safety_engine_v3")
    .select("*")
    .order("safety_score_v3", desc=True)
    .limit(20)
    .execute()
    .data
)

for r in rows:
    print(
        f'{r["home_team_name"]} vs {r["away_team_name"]} | '
        f'Pick: {r["pick"]} | '
        f'Score: {r["safety_score_v3"]} | '
        f'Status: {r["safety_status_v3"]} | '
        f'Label: {r["safety_label_v3"]}'
    )

    failed = r.get("failed_gates") or []
    if failed:
        print("   Failed:")
        for g in failed:
            print(f'   - {g["gate"]}: {g["note"]}')

    print()
    