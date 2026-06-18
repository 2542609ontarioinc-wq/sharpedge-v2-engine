alter table final_soccer_predictions
add column if not exists bookmaker text,
add column if not exists odds_decimal numeric,
add column if not exists odds_american integer,
add column if not exists market_implied_probability numeric,
add column if not exists model_edge numeric;
