-- Add confidence_tier to MLB final predictions table.
-- Values: 'Bet of the Day' | 'Elite' | 'Standard'
-- Assigned by calibrated-confidence rank within each daily engine run.
alter table mlb_final_predictions
  add column if not exists confidence_tier text;
