from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_parlays")
    .select("*")
    .order("created_at", desc=True)
    .limit(10)
    .execute()
    .data
)

for row in rows:
    print(row["parlay_type"], "| Combined:", row["combined_confidence"], "| Risk:", row["risk_level"])

    for leg in row["legs"]:
        print(
            " -",
            leg["game"],
            "|",
            leg["pick"],
            "|",
            leg["market"],
            "|",
            leg["confidence"],
            "|",
            leg["tier"],
        )

    print("-----")
    