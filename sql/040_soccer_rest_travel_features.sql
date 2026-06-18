create table if not exists soccer_rest_travel_features (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null unique,

    home_team_name text not null,
    away_team_name text not null,

    home_days_rest integer,
    away_days_rest integer,

    home_matches_last_7 integer default 0,
    away_matches_last_7 integer default 0,

    home_matches_last_14 integer default 0,
    away_matches_last_14 integer default 0,

    rest_advantage numeric default 0,
    congestion_score numeric default 0,
    travel_fatigue_score numeric default 0,

    created_at timestamptz default now()
);