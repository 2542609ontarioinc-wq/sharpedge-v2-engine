create table if not exists soccer_home_away_strength (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    home_team_home_form numeric,
    away_team_away_form numeric,

    home_away_difference numeric,

    created_at timestamptz default now()
);