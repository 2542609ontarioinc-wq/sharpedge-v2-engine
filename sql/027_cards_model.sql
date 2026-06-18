create table if not exists soccer_cards_predictions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    home_team_name text not null,
    away_team_name text not null,

    expected_cards numeric,
    over_35_probability numeric,
    over_45_probability numeric,

    cards_pick text,
    confidence numeric,

    created_at timestamptz default now()
);
