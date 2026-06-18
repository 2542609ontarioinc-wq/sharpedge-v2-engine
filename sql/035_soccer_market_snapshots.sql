create table if not exists soccer_market_snapshots (
    id uuid primary key default gen_random_uuid(),

    game_id uuid,

    home_team_name text,
    away_team_name text,

    market text,
    selection text,

    bookmaker text,

    odds_decimal numeric,
    odds_american integer,
    implied_probability numeric,

    snapshot_time timestamptz default now()
);