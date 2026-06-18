create table if not exists soccer_team_global_priors (
    id uuid primary key default gen_random_uuid(),

    team_name text not null unique,

    prior_attack_index numeric default 100,
    prior_defense_index numeric default 50,
    prior_cards_index numeric default 50,
    prior_corners_index numeric default 60,

    prior_style_label text default 'Balanced',

    source text default 'global_prior',

    created_at timestamptz default now()
);