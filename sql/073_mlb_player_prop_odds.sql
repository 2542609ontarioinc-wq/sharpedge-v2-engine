-- Raw player prop odds from The Odds API (per-event markets).
-- Purged and reloaded on each daily engine run (no unique key — same pattern as mlb_odds).

CREATE TABLE IF NOT EXISTS mlb_player_prop_odds (
    id                  bigserial primary key,
    game_id             uuid,
    odds_api_event_id   text,
    home_team_name      text,
    away_team_name      text,
    player_description  text,          -- player name as returned by The Odds API
    market_key          text,          -- pitcher_strikeouts, pitcher_outs_recorded, etc.
    bookmaker           text,
    side                text,          -- 'Over' or 'Under'
    line                numeric,
    odds_decimal        numeric,
    odds_american       integer,
    implied_probability numeric,
    sport_key           text not null default 'baseball_mlb',
    synced_at           timestamptz default now()
);

CREATE INDEX IF NOT EXISTS mlb_player_prop_odds_game_idx
    ON mlb_player_prop_odds (game_id);

CREATE INDEX IF NOT EXISTS mlb_player_prop_odds_player_mkt_idx
    ON mlb_player_prop_odds (player_description, market_key);
