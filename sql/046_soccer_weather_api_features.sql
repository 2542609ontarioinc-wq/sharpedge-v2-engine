alter table soccer_weather_features
add column if not exists venue_name text,
add column if not exists venue_city text,
add column if not exists venue_country text,
add column if not exists weather_status text,
add column if not exists weather_fetched_at timestamptz;
