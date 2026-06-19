-- Per-model grading for MLB model comparison.
-- One row per (game_id, model_version): grades the sharp pick only.
create table if not exists mlb_model_grades (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,
    model_version text not null,

    home_team_name text,
    away_team_name text,

    market text,
    pick text,

    raw_confidence numeric,
    calibrated_confidence numeric,
    odds_decimal numeric,
    odds_american integer,
    edge_flag text,
    model_edge numeric,
    no_odds boolean default false,

    home_score integer,
    away_score integer,
    total_runs integer,
    run_diff integer,

    grade text,           -- 'WIN', 'LOSS', 'VOID'
    units_result numeric,
    roi_percent numeric,

    graded_at timestamptz,

    unique(game_id, model_version)
);

create index if not exists idx_mlb_model_grades_version on mlb_model_grades(model_version);
create index if not exists idx_mlb_model_grades_grade   on mlb_model_grades(grade);
