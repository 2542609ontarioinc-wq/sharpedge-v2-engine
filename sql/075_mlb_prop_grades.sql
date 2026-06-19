-- Graded MLB player prop picks.
-- actual_value populated by grade_mlb_prop_picks.py via MLB Stats API game log.

CREATE TABLE IF NOT EXISTS mlb_prop_grades (
    id                  bigserial primary key,
    game_id             uuid,
    game_date           date,
    player_name         text,
    player_mlb_id       bigint,
    player_type         text,
    prop_market         text,
    market_line         numeric,
    pick_side           text,
    actual_value        numeric,   -- actual stat (Ks thrown, outs recorded, etc.)
    grade               text,      -- 'WIN', 'LOSS', 'VOID'
    edge_flag           text,
    best_odds_decimal   numeric,
    units_result        numeric,
    graded_at           timestamptz default now(),
    UNIQUE (game_id, player_mlb_id, prop_market)
);

CREATE INDEX IF NOT EXISTS mlb_prop_grades_game_idx ON mlb_prop_grades (game_id);
CREATE INDEX IF NOT EXISTS mlb_prop_grades_date_idx ON mlb_prop_grades (game_date);
