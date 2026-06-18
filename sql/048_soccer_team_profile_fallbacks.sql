create table if not exists soccer_team_profile_fallbacks (
    id uuid primary key default gen_random_uuid(),

    team_name text not null unique,

    matches_used integer default 0,

    fallback_attack_index numeric default 0,
    fallback_defense_index numeric default 0,
    fallback_cards_index numeric default 0,
    fallback_corners_index numeric default 0,

    fallback_style_label text,

    created_at timestamptz default now()
);
