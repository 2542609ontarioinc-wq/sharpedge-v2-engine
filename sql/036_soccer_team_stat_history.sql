create table if not exists soccer_team_stat_history (
    id uuid primary key default gen_random_uuid(),

    fixture_id text not null,
    game_id uuid,

    league_id text,
    league_name text,
    season text,

    game_date date,

    team_id text,
    team_name text,

    opponent_team_id text,
    opponent_team_name text,

    is_home boolean,

    goals_for integer default 0,
    goals_against integer default 0,

    shots_total integer default 0,
    shots_on_goal integer default 0,
    possession_percent numeric default 0,

    corners integer default 0,
    fouls integer default 0,
    yellow_cards integer default 0,
    red_cards integer default 0,

    raw_json jsonb,

    created_at timestamptz default now(),

    unique (fixture_id, team_id)
);
