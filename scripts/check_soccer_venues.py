from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

rows = (
    supabase.table("soccer_venues")
    .select("*")
    .order("venue_name")
    .limit(30)
    .execute()
    .data
)

for row in rows:
    print(
        row["venue_name"],
        "| City:",
        row["city"],
        "| Country:",
        row["country"],
        "| Surface:",
        row["surface"],
        "| Capacity:",
        row["capacity"],
    )