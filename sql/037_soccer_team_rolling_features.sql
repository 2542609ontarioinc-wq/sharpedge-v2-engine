create table if not exists soccer_team_rolling_features (
    id uuid primary key default gen_random_uuid(),

    team_name text not null,

    matches_used integer default 0,

    avg_goals_for numeric default 0,
    avg_goals_against numeric default 0,

    avg_shots_total numeric default 0,
    avg_shots_on_goal numeric default 0,

    avg_possession numeric default 0,

    avg_corners numeric default 0,
    avg_fouls numeric default 0,
    avg_yellow_cards numeric default 0,
    avg_red_cards numeric default 0,

    attacking_score numeric default 0,
    defensive_score numeric default 0,
    discipline_risk_score numeric default 0,
    corner_pressure_score numeric default 0,

    created_at timestamptz default now()
);
