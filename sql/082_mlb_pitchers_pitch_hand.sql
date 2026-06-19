-- Add pitcher handedness column to mlb_pitchers.
-- Populated by src/ingestion/sync_mlb_batter_stats.py (calls /people/{id} for each
-- starting pitcher, free MLB Stats API).  Used by the v4 lineup model to select
-- the correct batter handedness split (vL or vR) for the opposing lineup.

alter table mlb_pitchers
    add column if not exists pitch_hand text;  -- 'L', 'R', or 'S' (switch, rare)
