-- Add game_date to mlb_model_grades for manual auditing and date-sorted views.
-- Populated by grade_mlb_model_picks.py from the games table.

ALTER TABLE mlb_model_grades ADD COLUMN IF NOT EXISTS game_date date;

CREATE INDEX IF NOT EXISTS idx_mlb_model_grades_date ON mlb_model_grades (game_date);
