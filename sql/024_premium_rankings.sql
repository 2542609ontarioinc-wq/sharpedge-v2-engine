create table if not exists soccer_premium_rankings (
    id uuid primary key default gen_random_uuid(),

    rank integer,

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    best_pick text,
    market text,
    confidence numeric,
    ensemble_score numeric,
    value_rating text,

    tier text,

    created_at timestamptz default now()
);