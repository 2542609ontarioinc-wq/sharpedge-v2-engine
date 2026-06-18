create table if not exists soccer_injury_impact (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    total_injuries integer default 0,
    home_injuries integer default 0,
    away_injuries integer default 0,

    injury_available boolean default false,

    injury_impact_score numeric default 0,

    created_at timestamptz default now()
);
