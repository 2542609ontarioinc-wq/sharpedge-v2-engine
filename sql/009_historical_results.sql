create table if not exists soccer_historical_results (
    id uuid primary key default gen_random_uuid(),

    fixture_id text not null unique,

    sport_key text default 'soccer',

    league_id text,
    league_name text,
    country text,
    season text,

    game_date date,

    home_team_id text,
    away_team_id text,

    home_team_name text,
    away_team_name text,

    home_score integer,
    away_score integer,

    result text,
    total_goals integer,
    btts boolean,

    raw_json jsonb,

    created_at timestamptz default now()
);
