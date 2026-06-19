"""
Snapshot MLB main-market odds for closing-line value (CLV) tracking.

Runs hourly (14:00–03:00 UTC) as part of the refresh-batter-props job.
Uses a single bulk API call (h2h, totals, spreads) — 1 credit per run.
No per-event calls: alternate markets are captured only in the opening
snapshot (morning sync_mlb_odds run) and are excluded from CLV if not
present here. Props are never snapshotted.

Writes to mlb_odds_snapshots (append-only; never deletes).
The last snapshot whose captured_at < commence_time becomes the
effective closing line for CLV computation in build_mlb_clv.py.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY, ODDS_API_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"
TORONTO = ZoneInfo("America/Toronto")
BULK_ODDS_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"


def _decimal_to_american(dec):
    if not dec or dec <= 1:
        return None
    if dec >= 2:
        return int((dec - 1) * 100)
    return int(-100 / (dec - 1))


def _event_date_toronto(event):
    ct = event.get("commence_time", "")
    if not ct:
        return None
    try:
        dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
        return dt.astimezone(TORONTO).date().isoformat()
    except Exception:
        return None


def _find_game_id(home, away, event_date):
    q = (
        supabase.table("games")
        .select("id")
        .eq("sport_key", SPORT_KEY)
        .ilike("home_team_name", home)
        .ilike("away_team_name", away)
    )
    if event_date:
        q = q.eq("game_date", event_date)
    rows = q.limit(1).execute().data
    return rows[0]["id"] if rows else None


def main():
    resp = requests.get(
        BULK_ODDS_URL,
        params={
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h,totals,spreads",
            "oddsFormat": "decimal",
        },
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"Odds API error {resp.status_code}: {resp.text}")
        return

    remaining = resp.headers.get("x-requests-remaining", "?")
    print(f"  Odds API quota — remaining: {remaining}")

    events = resp.json()
    captured_at = datetime.now(timezone.utc).isoformat()
    rows = []

    for event in events:
        home = event.get("home_team")
        away = event.get("away_team")
        event_id = event.get("id")
        commence_time = event.get("commence_time")
        event_date = _event_date_toronto(event)
        game_id = _find_game_id(home, away, event_date)

        for bookmaker in event.get("bookmakers", []):
            book = bookmaker.get("title")
            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                for outcome in market.get("outcomes", []):
                    price = outcome.get("price")
                    if not price:
                        continue
                    rows.append({
                        "odds_api_event_id": event_id,
                        "game_id": game_id,
                        "home_team_name": home,
                        "away_team_name": away,
                        "market": market_key,
                        "selection": outcome.get("name"),
                        "line": outcome.get("point"),
                        "bookmaker": book,
                        "odds_decimal": price,
                        "odds_american": _decimal_to_american(price),
                        "implied_probability": round(1.0 / price * 100, 2),
                        "commence_time": commence_time,
                        "captured_at": captured_at,
                    })

    if rows:
        for i in range(0, len(rows), 500):
            supabase.table("mlb_odds_snapshots").insert(rows[i:i + 500]).execute()

    print(f"✅ MLB closing snapshot: {len(rows)} rows from {len(events)} events (captured_at={captured_at[:19]})")


if __name__ == "__main__":
    main()
