create table if not exists mlb_backtest_results (
    id uuid primary key default gen_random_uuid(),

    run_date date not null,
    market text not null,
    line numeric,

    total_predictions integer default 0,
    correct integer default 0,
    incorrect integer default 0,
    accuracy numeric,

    -- ROI assumes standard -110 juice unless real odds available
    avg_odds_decimal numeric,
    roi numeric,

    notes text,
    created_at timestamptz default now()
);
