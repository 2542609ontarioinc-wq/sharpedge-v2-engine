create table if not exists soccer_prediction_results (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    home_win_probability numeric,
    draw_probability numeric,
    away_win_probability numeric,

    predicted_winner text,
    confidence_score numeric,

    model_version text default 'winner_form_v1',

    created_at timestamptz default now()
);
