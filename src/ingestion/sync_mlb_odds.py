"""
Fetch MLB odds from The Odds API and upsert into mlb_odds.
Markets: h2h (moneyline), totals (over/under), spreads (run line),
         alternate_totals, alternate_spreads.

The bulk /odds endpoint does NOT support alternate markets — those are only
available via the per-event endpoint. So we make:
  - 1 bulk call for h2h, totals, spreads
  - 1 per-event call per game for alternate_totals + alternate_spreads combined
Total: ~16 API calls per daily run for a 15-game slate.

Alternate markets are stored with their original market key so that the
no-vig lookup functions can correctly pair legs from the same logical bet
without confusing standard ±1.5 with the alternate reversed-side ±1.5.
"""
import requests
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY, ODDS_API_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"
BULK_ODDS_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
EVENT_ODDS_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds"


def _decimal_to_american(dec):
    if not dec or dec <= 1:
        return None
    if dec >= 2:
        return int((dec - 1) * 100)
    return int(-100 / (dec - 1))


def _implied(dec):
    if not dec or dec <= 0:
        return None
    return round((1 / dec) * 100, 2)


def _find_game_id(home, away):
    rows = (
        supabase.table("games")
        .select("id")
        .eq("sport_key", SPORT_KEY)
        .ilike("home_team_name", home)
        .ilike("away_team_name", away)
        .limit(1)
        .execute()
        .data
    )
    return rows[0]["id"] if rows else None


def _save_bookmakers(bookmakers, home, away, game_id):
    saved = 0
    for bookmaker in bookmakers:
        book = bookmaker.get("title")
        for market in bookmaker.get("markets", []):
            market_key = market.get("key")
            for outcome in market.get("outcomes", []):
                price = outcome.get("price")
                row = {
                    "game_id": game_id,
                    "home_team_name": home,
                    "away_team_name": away,
                    "market": market_key,
                    "selection": outcome.get("name"),
                    "line": outcome.get("point"),
                    "bookmaker": book,
                    "odds_decimal": price,
                    "odds_american": _decimal_to_american(price) if price else None,
                    "implied_probability": _implied(price),
                }
                supabase.table("mlb_odds").insert(row).execute()
                saved += 1
    return saved


def main():
    # Purge all existing MLB odds before refreshing — prevents stale/duplicate
    # rows from accumulating across daily runs (table has no unique constraint).
    supabase.table("mlb_odds").delete().eq("sport_key", "baseball_mlb").execute()

    # --- Bulk call: main markets only (alternate_* not supported here) ---
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
    used = resp.headers.get("x-requests-used", "?")
    print(f"  Odds API quota after bulk call — used: {used}, remaining: {remaining}")

    events = resp.json()
    saved = 0

    for event in events:
        home = event.get("home_team")
        away = event.get("away_team")
        game_id = _find_game_id(home, away)
        saved += _save_bookmakers(event.get("bookmakers", []), home, away, game_id)

    print(f"  Main-market rows saved: {saved}")

    # --- Per-event calls: alternate markets (1 call per game, both alt markets combined) ---
    alt_saved = 0
    for event in events:
        event_id = event.get("id")
        home = event.get("home_team")
        away = event.get("away_team")
        game_id = _find_game_id(home, away)

        try:
            alt_resp = requests.get(
                EVENT_ODDS_URL.format(event_id=event_id),
                params={
                    "apiKey": ODDS_API_KEY,
                    "regions": "us",
                    "markets": "alternate_totals,alternate_spreads",
                    "oddsFormat": "decimal",
                },
                timeout=30,
            )
            if alt_resp.status_code != 200:
                print(f"  Alt odds skipped for {away}@{home}: {alt_resp.status_code}")
                continue
            alt_event = alt_resp.json()
            alt_saved += _save_bookmakers(alt_event.get("bookmakers", []), home, away, game_id)
        except Exception as exc:
            print(f"  Alt odds error for {away}@{home}: {exc}")

    print(f"  Alternate-market rows saved: {alt_saved}")
    print(f"  Total API calls this run: 1 bulk + {len(events)} per-event = {1 + len(events)}")
    print(f"✅ MLB odds rows saved: {saved + alt_saved}")


if __name__ == "__main__":
    main()
