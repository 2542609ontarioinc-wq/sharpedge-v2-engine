create table if not exists soccer_lineup_impact (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    home_lineup_count integer default 0,
    away_lineup_count integer default 0,

    lineup_available boolean default false,

    lineup_impact_score numeric default 0,

    created_at timestamptz default now()
);
