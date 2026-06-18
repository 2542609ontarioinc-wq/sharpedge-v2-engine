-- Per-market win-rate / ROI summary written by grade_mlb_results.py.
-- One row per market bucket: 'overall', 'moneyline', 'totals', 'run_line',
-- 'safe_balanced', 'safe_banker'.
create table if not exists mlb_pick_results (
    market        text         not null primary key,
    total_picks   int          not null default 0,
    wins          int          not null default 0,
    losses        int          not null default 0,
    voids         int          not null default 0,
    win_rate      numeric(5,2),
    total_units   numeric(10,2),
    roi_percent   numeric(6,2),
    updated_at    timestamptz  default now()
);
