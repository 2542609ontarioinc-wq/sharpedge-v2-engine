create table if not exists soccer_opponent_strength (
    id uuid primary key default gen_random_uuid(),

    team_name text not null unique,

    matches_used integer default 0,

    avg_opponent_attack numeric default 0,
    avg_opponent_defense numeric default 0,

    strength_of_schedule numeric default 0,
    adjusted_attack_index numeric default 0,
    adjusted_defense_index numeric default 0,

    created_at timestamptz default now()
);