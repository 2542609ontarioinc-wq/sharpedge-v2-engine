-- Add confidence_tier to soccer sharp picks tables.
-- Values: 'Bet of the Day' | 'Elite' | 'Standard'
-- Assigned by calibrated-confidence rank within each daily engine run.
alter table final_pro_soccer_picks
  add column if not exists confidence_tier text;

alter table final_pro_soccer_pick_history
  add column if not exists confidence_tier text;
