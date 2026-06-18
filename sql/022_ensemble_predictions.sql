create table if not exists soccer_ensemble_predictions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text,
    away_team_name text,

    winner_score numeric default 0,
    goals_score numeric default 0,
    btts_score numeric default 0,

    form_score numeric default 0,
    strength_score numeric default 0,
    home_away_score numeric default 0,

    lineup_score numeric default 0,
    injury_score numeric default 0,

    ensemble_score numeric default 0,

    created_at timestamptz default now()
);