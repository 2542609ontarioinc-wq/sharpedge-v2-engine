create table if not exists soccer_goal_predictions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    expected_home_goals numeric,
    expected_away_goals numeric,

    expected_total_goals numeric,

    over_25_probability numeric,
    under_25_probability numeric,

    btts_yes_probability numeric,
    btts_no_probability numeric,

    model_version text default 'goal_model_v1',

    created_at timestamptz default now()
);
