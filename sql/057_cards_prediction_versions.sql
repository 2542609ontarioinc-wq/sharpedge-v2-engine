create table if not exists soccer_cards_prediction_versions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    model_version text not null,

    home_team_name text not null,
    away_team_name text not null,

    expected_home_cards numeric,
    expected_away_cards numeric,
    expected_total_cards numeric,

    over_35_probability numeric,
    over_45_probability numeric,
    over_55_probability numeric,

    under_35_probability numeric,

    pick_label text,

    created_at timestamptz default now()
);
