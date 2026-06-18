create table if not exists soccer_weather_features (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null unique,

    home_team_name text not null,
    away_team_name text not null,

    temperature_c numeric,
    humidity numeric,
    wind_kph numeric,
    precipitation_mm numeric,

    weather_risk_score numeric default 0,
    goals_weather_modifier numeric default 0,
    corners_weather_modifier numeric default 0,

    source text default 'placeholder',

    created_at timestamptz default now()
);
