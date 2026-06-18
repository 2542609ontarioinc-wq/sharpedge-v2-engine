create table if not exists soccer_roi_market_bookmaker_league (
    id uuid primary key default gen_random_uuid(),

    market text,
    bookmaker text,
    league_key text,

    total_bets integer default 0,
    wins integer default 0,
    losses integer default 0,

    total_staked numeric default 0,
    profit_units numeric default 0,
    roi_percentage numeric default 0,

    created_at timestamptz default now()
);