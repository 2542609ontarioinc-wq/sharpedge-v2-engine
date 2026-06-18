create table if not exists soccer_venues (
    id uuid primary key default gen_random_uuid(),

    venue_id text unique,
    venue_name text,

    city text,
    country text,

    latitude numeric,
    longitude numeric,

    capacity integer,
    surface text,

    created_at timestamptz default now()
);
