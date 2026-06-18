create table if not exists final_pro_soccer_picks (
    game_id uuid primary key,

    home_team_name text,
    away_team_name text,

    pick text,
    market text,
    bookmaker text,

    final_value_rating numeric,
    final_tier text,

    raw_value_rating numeric,
    safety_score numeric,
    matchup_score numeric,

    final_allowed boolean default false,

    explanation text,

    created_at timestamptz default now()
);
