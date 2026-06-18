create table if not exists soccer_prediction_grades (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text,
    away_team_name text,

    predicted_winner text,
    actual_result text,

    winner_grade text,

    over_25_prediction text,
    actual_over_25 boolean,
    over_25_grade text,

    btts_prediction text,
    actual_btts boolean,
    btts_grade text,

    created_at timestamptz default now()
);
