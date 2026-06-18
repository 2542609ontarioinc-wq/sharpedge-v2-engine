create table if not exists soccer_prediction_versions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    model_version text not null,

    home_team_name text not null,
    away_team_name text not null,

    home_probability numeric,
    draw_probability numeric,
    away_probability numeric,

    predicted_winner text,
    confidence_score numeric,

    form_difference numeric,
    goal_difference_edge numeric,
    home_advantage_score numeric,

    created_at timestamptz default now()
);