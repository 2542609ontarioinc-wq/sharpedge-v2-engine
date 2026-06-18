create table if not exists soccer_btts_prediction_versions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    model_version text not null,

    home_team_name text not null,
    away_team_name text not null,

    expected_home_goals numeric,
    expected_away_goals numeric,

    btts_yes_probability numeric,
    btts_no_probability numeric,

    predicted_btts text,
    confidence_score numeric,

    created_at timestamptz default now()
);
