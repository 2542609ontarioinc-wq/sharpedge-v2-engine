create table if not exists mlb_pitchers (
    id uuid primary key default gen_random_uuid(),

    game_id uuid,           -- matches games(id)
    game_date date,
    side text,              -- 'home' or 'away'
    team_name text,
    pitcher_mlb_id integer,
    pitcher_name text,
    season integer,

    -- season stats at time of sync
    era text,               -- "3.12" as returned by MLB Stats API
    innings_pitched text,   -- "69.1" (X.Y where Y is outs, not decimal)
    runs_per_9 numeric,     -- RA9: actual runs allowed per 9 innings
    whip text,
    games_started integer,

    -- shrunk RA9 index: (ra9 / 4.5) shrunk toward 1.0 with K=5 starts
    -- <1.0 = better than average, >1.0 = worse than average
    shrunk_ra9_index numeric,

    raw_stats jsonb,
    synced_at timestamptz default now(),

    unique(game_id, side)
);

create index if not exists idx_mlb_pitchers_game on mlb_pitchers(game_id);
create index if not exists idx_mlb_pitchers_date on mlb_pitchers(game_date);
