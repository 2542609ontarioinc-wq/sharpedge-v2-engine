-- MLB player prop predictions: calibrated model output with market anchoring.
-- One row per (game_id, player_mlb_id, prop_market).
-- Calibration: 30% model / 70% market probability.
-- confidence_note: 'solid' (K, outs, H+R+RBI) or 'noisier' (ER, H, BB).

CREATE TABLE IF NOT EXISTS mlb_player_props (
    id                      bigserial primary key,
    game_id                 uuid,
    game_date               date,
    player_name             text not null,
    player_mlb_id           bigint,
    player_type             text not null,   -- 'pitcher' or 'batter'
    team_name               text,
    side                    text,            -- 'home' or 'away'
    prop_market             text not null,   -- 'strikeouts', 'outs_recorded', 'earned_runs',
                                             --   'hits_allowed', 'walks', 'h_r_rbi'
    model_projection        numeric,         -- expected per-game stat from season rates
    market_line             numeric,         -- market consensus posted line
    model_over_prob         numeric,         -- P(stat > market_line) per Poisson model
    market_novig_over_prob  numeric,         -- no-vig P(over) from market odds
    calibrated_over_prob    numeric,         -- 0.3 * model + 0.7 * market (or model if no-odds)
    pick_side               text,            -- 'Over' or 'Under'
    best_odds_decimal       numeric,
    best_odds_american      integer,
    model_edge              numeric,         -- calibrated_over_prob - market_novig_over_prob
    edge_flag               text,            -- 'REAL', 'suspect', 'no-odds'
    confidence_note         text,            -- 'solid' or 'noisier'
    confidence_tier         text,            -- 'Bet of the Day', 'Elite', 'Standard'
    updated_at              timestamptz default now(),
    UNIQUE (game_id, player_mlb_id, prop_market)
);

CREATE INDEX IF NOT EXISTS mlb_player_props_game_idx  ON mlb_player_props (game_id);
CREATE INDEX IF NOT EXISTS mlb_player_props_date_idx  ON mlb_player_props (game_date);
CREATE INDEX IF NOT EXISTS mlb_player_props_player_idx ON mlb_player_props (player_mlb_id);
