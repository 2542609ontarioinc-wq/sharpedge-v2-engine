from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
TORONTO = ZoneInfo("America/Toronto")
today = datetime.now(TORONTO).date()

preds = supabase.table("final_soccer_predictions").select("*").execute().data
games = supabase.table("games").select("*").eq("sport_key", "soccer").execute().data

game_map = {g["id"]: g for g in games}

shown = 0

for p in preds:
    g = game_map.get(p["game_id"], {})
    fixture = (g.get("raw_json") or {}).get("fixture") or {}
    dt_raw = fixture.get("date")

    if not dt_raw:
        continue

    dt = datetime.fromisoformat(dt_raw.replace("Z", "+00:00")).astimezone(TORONTO)

    if dt.date() != today:
        continue

    print(
        dt.strftime("%I:%M %p"),
        "|",
        p.get("home_team_name"),
        "vs",
        p.get("away_team_name"),
        "| Pick:",
        p.get("best_pick"),
        "| Market:",
        p.get("market"),
        "| Conf:",
        p.get("confidence"),
        "| Rating:",
        p.get("rating"),
        "| Rank Score:",
        p.get("ranking_score"),
    )
    shown += 1

print("Today watchlist rows:", shown)
