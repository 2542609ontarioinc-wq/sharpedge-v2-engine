create table if not exists predictions (

    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    sport_key text not null,

    model_version text not null,

    home_win_probability numeric,

    draw_probability numeric,

    away_win_probability numeric,

    expected_goals numeric,

    expected_cards numeric,

    expected_corners numeric,

    confidence_score numeric,

    created_at timestamptz default now()

);
