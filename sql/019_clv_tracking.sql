create table if not exists soccer_clv_tracking (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,
    market text not null,

    opening_odds numeric,
    closing_odds numeric,

    clv_difference numeric,
    beat_closing_line boolean,

    created_at timestamptz default now()
);
