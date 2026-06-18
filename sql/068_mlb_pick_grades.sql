-- Per-pick grading table for MLB picks.
-- Analogous to soccer_pick_grades_v2.
-- Upserted daily as games settle. One row per (game_id, market, pick).
create table if not exists mlb_pick_grades (
    id uuid primary key default gen_random_uuid(),

    game_id uuid,
    home_team_name text,
    away_team_name text,

    -- market: 'moneyline', 'totals', 'run_line', 'safe_balanced', 'safe_banker'
    market text,
    -- pick: 'New York Yankees', 'Over 8.5', 'Boston Red Sox -1.5', etc.
    pick text,

    raw_confidence numeric,
    calibrated_confidence numeric,
    odds_decimal numeric,
    odds_american integer,
    edge_flag text,       -- 'REAL', 'suspect', 'no-odds'
    model_edge numeric,
    no_odds boolean default false,

    -- actual result
    home_score integer,
    away_score integer,
    total_runs integer,
    run_diff integer,     -- home_score - away_score (positive = home win)

    grade text,           -- 'WIN', 'LOSS', 'VOID'
    units_result numeric, -- WIN: odds_decimal-1 (0 if no_odds), LOSS: -1, VOID: 0
    roi_percent numeric,

    graded_at timestamptz,

    unique(game_id, market, pick)
);

create index if not exists idx_mlb_pick_grades_game   on mlb_pick_grades(game_id);
create index if not exists idx_mlb_pick_grades_market on mlb_pick_grades(market);
create index if not exists idx_mlb_pick_grades_grade  on mlb_pick_grades(grade);
