create table if not exists soccer_odds (
    id uuid primary key default gen_random_uuid(),

    game_id uuid,
    sport_key text default 'soccer',

    home_team_name text,
    away_team_name text,

    market text,
    selection text,

    bookmaker text,
    odds_decimal numeric,
    odds_american integer,

    implied_probability numeric,

    captured_at timestamptz default now()
);
