create table if not exists soccer_match_strength (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    home_form_score numeric,
    away_form_score numeric,

    form_difference numeric,

    predicted_edge text,

    created_at timestamptz default now()
);
