create table if not exists mlb_odds (
    id uuid primary key default gen_random_uuid(),

    game_id uuid,
    sport_key text default 'baseball_mlb',

    home_team_name text,
    away_team_name text,

    market text,       -- 'h2h', 'totals', 'spreads'
    selection text,    -- team name, 'Over', 'Under'
    line numeric,      -- e.g. 7.5, 8.5, -1.5, +1.5

    bookmaker text,
    odds_decimal numeric,
    odds_american integer,
    implied_probability numeric,

    captured_at timestamptz default now()
);

create index if not exists idx_mlb_odds_game on mlb_odds(game_id);
create index if not exists idx_mlb_odds_market on mlb_odds(game_id, market);
