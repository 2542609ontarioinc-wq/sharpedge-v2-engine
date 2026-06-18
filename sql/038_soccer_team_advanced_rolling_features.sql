create table if not exists soccer_team_advanced_rolling_features (
    id uuid primary key default gen_random_uuid(),

    team_name text not null unique,

    matches_used integer default 0,

    weighted_goals_for numeric default 0,
    weighted_goals_against numeric default 0,
    weighted_shots_total numeric default 0,
    weighted_shots_on_goal numeric default 0,
    weighted_possession numeric default 0,
    weighted_corners numeric default 0,
    weighted_fouls numeric default 0,
    weighted_yellow_cards numeric default 0,

    home_goals_for numeric default 0,
    home_goals_against numeric default 0,
    home_shots_total numeric default 0,
    home_corners numeric default 0,

    away_goals_for numeric default 0,
    away_goals_against numeric default 0,
    away_shots_total numeric default 0,
    away_corners numeric default 0,

    attack_index numeric default 0,
    defense_index numeric default 0,
    cards_index numeric default 0,
    corners_index numeric default 0,

    created_at timestamptz default now()
);
