-- Confirmed MLB batting lineups with season hitting stats (from MLB Stats API).
-- Populated by sync_mlb_lineups.py when lineups are confirmed before first pitch.
-- Used by generate_mlb_player_props.py to build batter H+R+RBI props.

CREATE TABLE IF NOT EXISTS mlb_lineups (
    id                  bigserial primary key,
    game_id             uuid,
    game_date           date,
    side                text,       -- 'home' or 'away'
    team_name           text,
    batting_order       int,        -- 1-9
    player_mlb_id       bigint,
    player_name         text,
    season              int,
    games_played        int,
    at_bats             int,
    hits                int,
    runs                int,
    rbi                 int,
    avg_hrr_per_game    numeric,    -- (hits + runs + rbi) / games_played
    raw_stats           jsonb,
    synced_at           timestamptz default now(),
    UNIQUE (game_id, side, batting_order)
);

CREATE INDEX IF NOT EXISTS mlb_lineups_game_idx ON mlb_lineups (game_id);
CREATE INDEX IF NOT EXISTS mlb_lineups_date_idx ON mlb_lineups (game_date);
