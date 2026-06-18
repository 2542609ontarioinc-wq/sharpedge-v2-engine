create table if not exists soccer_prediction_analytics (
    id uuid primary key default gen_random_uuid(),

    report_name text not null,
    total_graded integer default 0,

    winner_wins integer default 0,
    winner_losses integer default 0,
    winner_accuracy numeric default 0,

    over_25_wins integer default 0,
    over_25_losses integer default 0,
    over_25_accuracy numeric default 0,

    btts_wins integer default 0,
    btts_losses integer default 0,
    btts_accuracy numeric default 0,

    created_at timestamptz default now()
);
