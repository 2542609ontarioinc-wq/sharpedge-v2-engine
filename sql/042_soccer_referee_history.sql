create table if not exists soccer_referee_history (
    id uuid primary key default gen_random_uuid(),

    referee_name text not null unique,

    matches_used integer default 0,

    avg_yellow_cards numeric default 0,
    avg_red_cards numeric default 0,
    avg_fouls numeric default 0,
    avg_corners numeric default 0,
    avg_goals numeric default 0,

    card_strictness_score numeric default 0,
    game_flow_score numeric default 0,

    created_at timestamptz default now()
);
