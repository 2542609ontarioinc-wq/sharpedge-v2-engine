create table if not exists soccer_match_features (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null unique,

    sport_key text default 'soccer',

    league_key text,
    league_name text,
    country text,
    season text,
    round text,

    game_date date,

    home_team_name text,
    away_team_name text,

    home_form_score numeric,
    away_form_score numeric,
    form_difference numeric,

    home_goals_for integer,
    home_goals_against integer,
    away_goals_for integer,
    away_goals_against integer,

    home_expected_goals numeric,
    away_expected_goals numeric,
    expected_total_goals numeric,

    winner_pick text,
    winner_confidence numeric,

    goals_pick text,
    goals_confidence numeric,

    btts_pick text,
    btts_confidence numeric,

    best_pick text,
    best_market text,
    best_confidence numeric,

    bookmaker text,
    odds_decimal numeric,
    odds_american integer,
    market_implied_probability numeric,
    model_edge numeric,

    has_form boolean default false,
    has_odds boolean default false,
    has_lineup boolean default false,
    has_injury_data boolean default false,

    data_quality_score numeric default 0,
    allowed_for_premium boolean default false,

    created_at timestamptz default now()
);