-- Per-model pick generation for MLB model comparison (v2–v7).
-- Stores the best sharp pick per (game_id, model_version).
-- v2 production picks remain in mlb_final_predictions; this table is shadow-only.
create table if not exists mlb_model_picks (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,
    model_version text not null,

    home_team_name text,
    away_team_name text,

    best_pick text,
    market text,  -- 'moneyline', 'totals', 'run_line'
    raw_confidence numeric,
    calibrated_confidence numeric,

    odds_decimal numeric,
    odds_american integer,
    market_implied_probability numeric,
    model_edge numeric,
    edge_flag text,  -- 'REAL', 'suspect', 'no-odds'

    -- balanced safe-zone pick (prob only; odds not stored here)
    balanced_pick text,
    balanced_prob numeric,

    updated_at timestamptz default now(),

    unique(game_id, model_version)
);

create index if not exists idx_mlb_model_picks_game    on mlb_model_picks(game_id);
create index if not exists idx_mlb_model_picks_version on mlb_model_picks(model_version);
