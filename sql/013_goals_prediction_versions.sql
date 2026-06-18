create table if not exists soccer_goals_prediction_versions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    model_version text not null,

    home_team_name text not null,
    away_team_name text not null,

    expected_home_goals numeric,
    expected_away_goals numeric,
    expected_total_goals numeric,

    over_15_probability numeric,
    over_25_probability numeric,
    over_35_probability numeric,

    under_25_probability numeric,

    btts_yes_probability numeric,
    btts_no_probability numeric,

    created_at timestamptz default now()
);
