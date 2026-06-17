from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_adaptive_weights_v1")
    .select("*")
    .order("sample_size", desc=True)
    .limit(30)
    .execute()
    .data
)

for r in rows:
    print(
        f'{r["segment_type"]}: {r["segment_value"]} | '
        f'Sample: {r["sample_size"]} | '
        f'ROI: {r["roi_percent"]}% | '
        f'Win: {r["win_rate"]}% | '
        f'Weight: {r["adaptive_weight"]} | '
        f'Confidence: {r["confidence_level"]}'
    )
    print("  ", r.get("engine_note"))
