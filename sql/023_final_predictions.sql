create table if not exists final_soccer_predictions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    best_pick text,
    market text,
    confidence numeric,

    secondary_pick text,
    secondary_market text,
    secondary_confidence numeric,

    value_rating text,
    ensemble_score numeric,

    created_at timestamptz default now()
);
