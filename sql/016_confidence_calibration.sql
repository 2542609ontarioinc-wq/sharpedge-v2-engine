create table if not exists confidence_calibration (
    id uuid primary key default gen_random_uuid(),

    prediction_type text not null,
    confidence_bucket integer not null,

    total_predictions integer not null default 0,
    wins integer not null default 0,
    losses integer not null default 0,

    actual_win_rate numeric(6,2) not null default 0,

    created_at timestamptz default now()
);
