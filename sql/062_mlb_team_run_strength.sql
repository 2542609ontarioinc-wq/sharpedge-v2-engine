create table if not exists mlb_team_run_strength (
    id uuid primary key default gen_random_uuid(),

    team_name text unique,
    season text,
    games_played integer default 0,

    avg_runs_scored numeric,
    avg_runs_allowed numeric,
    league_avg_runs numeric,

    -- raw index (team avg / league avg)
    run_scoring_index numeric,
    run_allowed_index numeric,

    -- shrunk toward 1.0 with SHRINK_K=5
    shrunk_scoring_index numeric,
    shrunk_allowed_index numeric,

    updated_at timestamptz default now()
);
