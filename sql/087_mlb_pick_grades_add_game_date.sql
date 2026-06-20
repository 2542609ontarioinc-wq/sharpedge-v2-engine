-- Add game_date to mlb_pick_grades for manual auditing and date-sorted views.
-- Populated by grade_mlb_picks.py from the games table.

ALTER TABLE mlb_pick_grades ADD COLUMN IF NOT EXISTS game_date date;

CREATE INDEX IF NOT EXISTS idx_mlb_pick_grades_date ON mlb_pick_grades (game_date);
