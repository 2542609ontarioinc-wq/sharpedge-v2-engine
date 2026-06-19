create table if not exists mlb_final_predictions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid unique,
    home_team_name text,
    away_team_name text,

    -- best pick (highest calibrated edge)
    best_pick text,
    market text,       -- 'moneyline', 'totals', 'run_line'
    raw_confidence numeric,
    calibrated_confidence numeric,

    -- real-market odds alignment
    bookmaker text,
    odds_decimal numeric,
    odds_american integer,
    market_implied_probability numeric,
    model_edge numeric,
    edge_flag text,    -- 'REAL', 'suspect', 'no-odds'

    -- second-best pick
    secondary_pick text,
    secondary_market text,
    secondary_confidence numeric,

    updated_at timestamptz default now()
);

create index if not exists idx_mlb_final_pred_game on mlb_final_predictions(game_id);
