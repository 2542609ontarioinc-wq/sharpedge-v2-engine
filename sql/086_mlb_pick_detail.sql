-- Enriched per-pick diagnostic table for graded MLB game picks.
-- Populated by src/grading/build_mlb_pick_detail.py after grading.
-- Joins mlb_pick_grades + mlb_run_predictions + mlb_clv_tracking + games.
-- DIAGNOSTIC ONLY — read-only from the web; does not affect any pick or model logic.

CREATE TABLE IF NOT EXISTS mlb_pick_detail (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    game_id  uuid NOT NULL,
    game_date date,
    home_team text,
    away_team text,

    -- Pick
    market    text,     -- 'moneyline', 'totals', 'run_line', 'safe_balanced', 'safe_banker'
    pick      text,
    pick_line numeric,  -- numeric threshold: 8.5 for "Over 8.5", -1.5 for "Team -1.5"
    pick_side text,     -- 'home', 'away', 'over', 'under'
    is_home_pick boolean,
    is_over      boolean,
    is_favorite  boolean,  -- true when implied prob > 50% (odds_decimal < 2.0)

    -- Model at pick time
    model_proj_total numeric,  -- expected total runs (preferred model version)
    model_proj_home  numeric,
    model_proj_away  numeric,
    calibrated_conf  numeric,  -- calibrated probability % (50–100 scale)
    raw_confidence   numeric,
    model_edge       numeric,
    edge_bucket      text,     -- '<2%', '2-5%', '5%+'
    conf_bucket      text,     -- '<55%', '55-65%', '65-75%', '75%+'
    odds_decimal     numeric,
    edge_flag        text,
    no_odds          boolean DEFAULT false,

    -- Actual result
    home_score   integer,
    away_score   integer,
    actual_total integer,
    actual_diff  integer,

    -- Model error: positive = model projected too high
    total_bias numeric,

    -- Grade
    grade        text,    -- 'WIN', 'LOSS', 'VOID'
    units_result numeric,
    roi_percent  numeric,

    -- Closing-line value (null until closing odds are captured regularly)
    clv        numeric,
    beat_close boolean,

    graded_at timestamptz,

    UNIQUE(game_id, market, pick)
);

CREATE INDEX IF NOT EXISTS idx_mlb_pick_detail_date   ON mlb_pick_detail(game_date);
CREATE INDEX IF NOT EXISTS idx_mlb_pick_detail_market ON mlb_pick_detail(market);
CREATE INDEX IF NOT EXISTS idx_mlb_pick_detail_grade  ON mlb_pick_detail(grade);
CREATE INDEX IF NOT EXISTS idx_mlb_pick_detail_conf   ON mlb_pick_detail(conf_bucket);

-- Enriched per-prop diagnostic table for graded MLB player prop picks.
-- Populated by src/grading/build_mlb_prop_detail.py after grading.
-- Joins mlb_prop_grades + mlb_player_props (model_projection, calibrated_prob, model_edge).

CREATE TABLE IF NOT EXISTS mlb_prop_detail (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    game_id       uuid NOT NULL,
    game_date     date,
    player_name   text,
    player_mlb_id bigint,
    player_type   text,      -- 'pitcher', 'batter'
    prop_market   text,

    -- Pick at pick time
    market_line       numeric,
    pick_side         text,    -- 'Over', 'Under'
    model_projection  numeric, -- model's predicted stat value
    calibrated_prob   numeric, -- calibrated over-probability %
    model_edge        numeric,
    best_odds_decimal numeric,
    edge_flag         text,

    -- Actual
    actual_value numeric,
    prop_bias    numeric,  -- model_projection - actual_value (positive = model too high)

    -- Grade
    grade        text,
    units_result numeric,

    graded_at timestamptz,

    UNIQUE(game_id, player_mlb_id, prop_market)
);

CREATE INDEX IF NOT EXISTS idx_mlb_prop_detail_date   ON mlb_prop_detail(game_date);
CREATE INDEX IF NOT EXISTS idx_mlb_prop_detail_market ON mlb_prop_detail(prop_market);
CREATE INDEX IF NOT EXISTS idx_mlb_prop_detail_grade  ON mlb_prop_detail(grade);
