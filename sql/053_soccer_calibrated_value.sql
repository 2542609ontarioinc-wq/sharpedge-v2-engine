create table if not exists soccer_calibrated_value (
    game_id uuid primary key,

    home_team_name text,
    away_team_name text,

    pick text,
    market text,
    bookmaker text,

    raw_value_rating numeric,
    safety_score numeric,
    matchup_score numeric,

    confidence_dampener numeric,
    sample_dampener numeric,
    final_value_rating numeric,

    final_tier text,
    final_allowed boolean default false,

    notes text,

    created_at timestamptz default now()
);
