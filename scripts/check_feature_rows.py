from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY
)

result = (
    supabase.table("model_features")
    .select("*")
    .limit(20)
    .execute()
)

print(f"Feature rows: {len(result.data)}")

for row in result.data[:5]:
    print(
        row["sport_key"],
        row["feature_version"],
        row["data_quality_score"]
    )
    