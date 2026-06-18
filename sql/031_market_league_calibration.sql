create table if not exists soccer_market_league_calibration (
    id uuid primary key default gen_random_uuid(),

    market text not null,
    league_key text,
    confidence_bucket integer not null,

    total_predictions integer default 0,
    wins integer default 0,
    losses integer default 0,

    actual_win_rate numeric default 0,

    created_at timestamptz default now()
);
