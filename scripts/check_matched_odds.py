from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

matched = (
    supabase.table("soccer_odds")
    .select("id")
    .not_.is_("game_id", "null")
    .execute()
    .data
)

unmatched = (
    supabase.table("soccer_odds")
    .select("id")
    .is_("game_id", "null")
    .execute()
    .data
)

print("Matched odds rows:", len(matched))
print("Unmatched odds rows:", len(unmatched))
