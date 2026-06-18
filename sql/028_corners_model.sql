create table if not exists soccer_corners_predictions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    expected_corners numeric,
    over_75_probability numeric,
    over_85_probability numeric,
    over_95_probability numeric,

    corners_pick text,
    confidence numeric,

    created_at timestamptz default now()
);
