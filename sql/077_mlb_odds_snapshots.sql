-- Append-only odds snapshot history for MLB game markets.
-- Written by sync_mlb_odds (opening, morning run) and snap_mlb_odds_closing (hourly).
-- NEVER deleted — preserves the full price timeline needed for CLV computation.
-- Covers main game markets only: h2h, totals, spreads, alternate_totals, alternate_spreads.
-- Player props are NOT stored here (no clean 2-sided de-vig available for props).
create table if not exists mlb_odds_snapshots (
    id uuid primary key default gen_random_uuid(),

    odds_api_event_id text,
    game_id uuid,

    home_team_name text,
    away_team_name text,

    market text,       -- 'h2h', 'totals', 'spreads', 'alternate_totals', 'alternate_spreads'
    selection text,    -- team name, 'Over', 'Under'
    line numeric,

    bookmaker text,
    odds_decimal numeric,
    odds_american integer,
    implied_probability numeric,

    -- Game start time from Odds API. Used to filter "before first pitch" for true closing line.
    commence_time timestamptz,
    captured_at timestamptz default now()
);

create index if not exists idx_mlb_odds_snaps_game     on mlb_odds_snapshots(game_id);
create index if not exists idx_mlb_odds_snaps_event    on mlb_odds_snapshots(odds_api_event_id, market, captured_at);
create index if not exists idx_mlb_odds_snaps_captured on mlb_odds_snapshots(captured_at);
