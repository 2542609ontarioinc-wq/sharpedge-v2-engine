alter table soccer_match_features
add column if not exists opponent_strength_of_schedule numeric,
add column if not exists home_adjusted_attack_index numeric,
add column if not exists away_adjusted_attack_index numeric,
add column if not exists home_adjusted_defense_index numeric,
add column if not exists away_adjusted_defense_index numeric,

add column if not exists home_style_label text,
add column if not exists away_style_label text,
add column if not exists home_high_card_risk boolean,
add column if not exists away_high_card_risk boolean,
add column if not exists home_high_corner_team boolean,
add column if not exists away_high_corner_team boolean,

add column if not exists league_avg_goals numeric,
add column if not exists league_avg_corners numeric,
add column if not exists league_avg_yellow_cards numeric,
add column if not exists league_btts_rate numeric,
add column if not exists league_over_25_rate numeric,

add column if not exists home_days_rest integer,
add column if not exists away_days_rest integer,
add column if not exists rest_advantage numeric,
add column if not exists congestion_score numeric,

add column if not exists venue_name text,
add column if not exists venue_city text,
add column if not exists temperature_c numeric,
add column if not exists wind_kph numeric,
add column if not exists precipitation_mm numeric,
add column if not exists weather_risk_score numeric,
add column if not exists goals_weather_modifier numeric,
add column if not exists corners_weather_modifier numeric;