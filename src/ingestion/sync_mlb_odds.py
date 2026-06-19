"""
Fetch MLB odds from The Odds API and upsert into mlb_odds and mlb_player_prop_odds.

Markets fetched:
  Bulk call (1):      h2h, totals, spreads
  Per-event call (N): alternate_totals, alternate_spreads,
                      pitcher_strikeouts, pitcher_outs_recorded, pitcher_earned_runs,
                      pitcher_hits_allowed, pitcher_walks, batter_hits_runs_rbis

The bulk /odds endpoint does NOT support alternate or player-prop markets —
those are only available via the per-event endpoint.  All non-bulk markets are
combined into a SINGLE per-event call per game so that total API credits used
stays at 1 bulk + N per-event (same as before — extending the markets param
does not cost extra credits).

Routing:
  - Outcomes WITH a 'description' field (player name) → mlb_player_prop_odds
  - Outcomes WITHOUT a 'description' field            → mlb_odds (alt totals/spreads)

Both tables are purged at the start of each run (same pattern as before).
"""
import requests
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY, ODDS_API_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

SPORT_KEY = "baseball_mlb"
BULK_ODDS_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
EVENT_ODDS_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds"

# Markets combined into one per-event call to keep total API credits at 1+N.
PROP_MARKET_KEYS = {
    "pitcher_strikeouts",
    "pitcher_outs",         # Odds API key is 'pitcher_outs', not 'pitcher_outs_recorded'
    "pitcher_earned_runs",
    "pitcher_hits_allowed",
    "pitcher_walks",
    "batter_hits_runs_rbis",
}
PER_EVENT_MARKETS = (
    "alternate_totals,alternate_spreads,"
    "pitcher_strikeouts,pitcher_outs,pitcher_earned_runs,"
    "pitcher_hits_allowed,pitcher_walks,batter_hits_runs_rbis"
)


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
    # Purge stale rows before refreshing (no unique constraint on either table).
    supabase.table("mlb_odds").delete().eq("sport_key", "baseball_mlb").execute()
    supabase.table("mlb_player_prop_odds").delete().eq("sport_key", "baseball_mlb").execute()

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

    # --- Per-event calls: alt markets + player props in ONE combined call per game ---
    # Combining them keeps total API credits at 1 bulk + N per-event (no extra cost).
    alt_saved = prop_saved = 0
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
                    "markets": PER_EVENT_MARKETS,
                    "oddsFormat": "decimal",
                },
                timeout=30,
            )
            if alt_resp.status_code != 200:
                print(f"  Per-event skipped for {away}@{home}: {alt_resp.status_code}")
                continue
            alt_event = alt_resp.json()
        except Exception as exc:
            print(f"  Per-event error for {away}@{home}: {exc}")
            continue

        # Route: outcomes with 'description' (player name) → prop table;
        #        outcomes without 'description' → game odds table (alt totals/spreads).
        game_bookmakers = []
        prop_rows = []

        for bookmaker in alt_event.get("bookmakers", []):
            book_title = bookmaker.get("title")
            game_markets = []
            for market in bookmaker.get("markets", []):
                mkt_key = market.get("key")
                if mkt_key in PROP_MARKET_KEYS:
                    for outcome in market.get("outcomes", []):
                        dec = outcome.get("price")
                        prop_rows.append({
                            "game_id": game_id,
                            "odds_api_event_id": event_id,
                            "home_team_name": home,
                            "away_team_name": away,
                            "player_description": outcome.get("description"),
                            "market_key": mkt_key,
                            "bookmaker": book_title,
                            "side": outcome.get("name"),
                            "line": outcome.get("point"),
                            "odds_decimal": dec,
                            "odds_american": _decimal_to_american(dec) if dec else None,
                            "implied_probability": round(1 / dec * 100, 2) if dec else None,
                            "sport_key": SPORT_KEY,
                        })
                else:
                    game_markets.append(market)
            if game_markets:
                game_bookmakers.append({**bookmaker, "markets": game_markets})

        alt_saved += _save_bookmakers(game_bookmakers, home, away, game_id)
        if prop_rows:
            supabase.table("mlb_player_prop_odds").insert(prop_rows).execute()
            prop_saved += len(prop_rows)

    print(f"  Alternate-market rows saved: {alt_saved}")
    print(f"  Player prop odds rows saved: {prop_saved}")
    print(f"  Total API calls this run: 1 bulk + {len(events)} per-event = {1 + len(events)}")
    print(f"✅ MLB odds rows saved: {saved + alt_saved} game | {prop_saved} prop")


if __name__ == "__main__":
    main()
