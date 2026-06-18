create table if not exists soccer_matchup_features (

    game_id bigint primary key,

    home_team text,
    away_team text,

    attack_edge numeric,
    defense_edge numeric,

    corner_edge numeric,
    card_edge numeric,

    style_matchup text,

    possession_advantage numeric,
    transition_advantage numeric,
    pressing_advantage numeric,

    referee_fit numeric,
    weather_fit numeric,

    rest_edge numeric,
    travel_edge numeric,

    sos_edge numeric,

    home_advantage numeric,

    tactical_edge numeric,

    overall_matchup_score numeric,

    created_at timestamptz default now()
);