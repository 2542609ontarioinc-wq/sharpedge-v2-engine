-- 090_mlb_live_state.sql
-- Live linescore state for MLB games that have active picks.
-- Written by sync_mlb_live_state.py every hour; display-only,
-- never touches mlb_pick_grades or mlb_prop_grades.

CREATE TABLE IF NOT EXISTS mlb_live_state (
    game_id       text PRIMARY KEY,
    home_score    integer,
    away_score    integer,
    inning        integer,
    inning_half   text,        -- 'Top' | 'Bottom' | null when not live
    outs          integer,
    game_status   text,        -- 'Live' | 'Final' | 'Preview' | 'Postponed' | etc.
    home_pitcher  text,        -- probable/scheduled starter
    away_pitcher  text,
    captured_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mlb_live_state_status
    ON mlb_live_state(game_status);
