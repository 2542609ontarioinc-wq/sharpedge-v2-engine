create table if not exists soccer_model_safety_flags (
    game_id uuid primary key,

    home_team_name text,
    away_team_name text,

    sample_size_risk boolean default false,
    missing_odds_risk boolean default false,
    missing_weather_risk boolean default false,
    extreme_model_risk boolean default false,

    safety_score numeric default 100,
    value_cap numeric default 100,

    final_allowed boolean default false,
    safety_notes text,

    created_at timestamptz default now()
);
