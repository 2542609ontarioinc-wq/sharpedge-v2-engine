create table if not exists prediction_models (

    id uuid primary key default gen_random_uuid(),

    sport_key text not null,

    model_name text not null,

    model_version text not null,

    active boolean default true,

    created_at timestamptz default now()

);