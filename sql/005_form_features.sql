create table if not exists soccer_form_features (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,

    team_id uuid,
    team_name text not null,

    sport_key text default 'soccer',
    league_key text,

    matches_checked integer default 0,

    wins integer default 0,
    draws integer default 0,
    losses integer default 0,

    goals_for integer default 0,
    goals_against integer default 0,

    form_score numeric default 0,

    created_at timestamptz default now()
);
