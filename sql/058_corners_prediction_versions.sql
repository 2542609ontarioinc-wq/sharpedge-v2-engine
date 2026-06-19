create table if not exists soccer_corners_prediction_versions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    model_version text not null,

    home_team_name text not null,
    away_team_name text not null,

    expected_home_corners numeric,
    expected_away_corners numeric,
    expected_total_corners numeric,

    over_85_probability numeric,
    over_95_probability numeric,
    over_105_probability numeric,

    under_95_probability numeric,

    pick_label text,

    created_at timestamptz default now()
);
