-- Rolling per-model analytics for MLB model comparison.
-- One row per model_version; updated daily after grading.
-- PRIMARY judges: mae_total_xr (calibration) and avg_clv (closing-line value).
-- SECONDARY judges: win_rate, roi_percent (can be gamed by favorites bias — see labels).
create table if not exists mlb_model_analytics (
    id uuid primary key default gen_random_uuid(),

    model_version text not null unique,

    games_graded integer,
    picks_with_real_odds integer,  -- excludes no-odds; only these count for ROI

    -- PRIMARY: calibration accuracy
    mae_total_xr numeric,          -- MAE on expected total runs vs actuals (↓ = better)
    brier_score numeric,           -- probability calibration score (↓ = better)
    over85_accuracy numeric,       -- O/U 8.5 direction accuracy (↑ = better)
    direction_accuracy numeric,    -- moneyline direction correct % (↑ = better)

    -- SECONDARY: pick performance (subject to favorites bias — do not use alone)
    win_rate numeric,              -- WIN fraction across all picks
    win_rate_real_odds numeric,    -- WIN fraction for REAL-odds picks only
    roi_units numeric,             -- total units P/L (real-odds picks; no-odds excluded)
    roi_percent numeric,           -- roi_units / picks_with_real_odds * 100

    -- CLV: null until mlb_odds_snapshots captures closing prices
    avg_clv numeric,

    updated_at timestamptz default now()
);
