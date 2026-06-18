create table if not exists soccer_team_style_profiles (
    id uuid primary key default gen_random_uuid(),

    team_name text not null unique,

    style_label text,

    possession_style boolean default false,
    high_press_style boolean default false,
    direct_style boolean default false,
    crossing_style boolean default false,
    defensive_style boolean default false,
    high_tempo_style boolean default false,
    high_card_risk boolean default false,
    high_corner_team boolean default false,

    attack_index numeric default 0,
    defense_index numeric default 0,
    cards_index numeric default 0,
    corners_index numeric default 0,

    created_at timestamptz default now()
);