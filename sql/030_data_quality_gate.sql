create table if not exists soccer_data_quality_gate (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    has_form boolean default false,
    has_odds boolean default false,
    has_lineup boolean default false,
    has_injury_data boolean default false,

    quality_score numeric default 0,

    allowed_for_premium boolean default false,

    block_reason text,

    created_at timestamptz default now()
);
