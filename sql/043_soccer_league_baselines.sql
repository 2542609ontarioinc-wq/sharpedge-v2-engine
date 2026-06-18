create table if not exists soccer_league_baselines (
    id uuid primary key default gen_random_uuid(),

    league_id text not null unique,
    league_name text,

    matches_used integer default 0,

    avg_goals numeric default 0,
    avg_shots numeric default 0,
    avg_shots_on_goal numeric default 0,
    avg_possession numeric default 0,
    avg_corners numeric default 0,
    avg_fouls numeric default 0,
    avg_yellow_cards numeric default 0,
    avg_red_cards numeric default 0,

    btts_rate numeric default 0,
    over_25_rate numeric default 0,

    created_at timestamptz default now()
);
