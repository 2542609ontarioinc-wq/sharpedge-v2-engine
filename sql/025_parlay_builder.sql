create table if not exists soccer_parlays (
    id uuid primary key default gen_random_uuid(),

    parlay_type text not null,

    legs jsonb not null,

    combined_confidence numeric,
    risk_level text,

    created_at timestamptz default now()
);
