-- Add subscriber qualification flags to mlb_pick_detail.
-- Computed by build_mlb_pick_detail.py using subscriber_thresholds.py.
ALTER TABLE mlb_pick_detail
  ADD COLUMN IF NOT EXISTS subscriber_qualified boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS bet_of_day           boolean DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_mlb_pick_detail_sub
  ON mlb_pick_detail(subscriber_qualified) WHERE subscriber_qualified = true;

-- Add subscriber qualification flags to mlb_prop_detail.
-- Computed by build_mlb_prop_detail.py using subscriber_thresholds.py.
ALTER TABLE mlb_prop_detail
  ADD COLUMN IF NOT EXISTS subscriber_qualified boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS bet_of_day           boolean DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_mlb_prop_detail_sub
  ON mlb_prop_detail(subscriber_qualified) WHERE subscriber_qualified = true;

-- Subscriber track record aggregates.
-- Populated by src/analytics/build_mlb_subscriber_analytics.py.
-- One row per segment: 'all' (all qualifying plays) and 'bet_of_day'.
CREATE TABLE IF NOT EXISTS mlb_subscriber_results (
  segment          text PRIMARY KEY,   -- 'all' | 'bet_of_day'
  pick_count       integer,            -- total graded (WIN + LOSS, excluding VOID)
  win_count        integer,
  loss_count       integer,
  win_rate         double precision,   -- fraction 0–1
  units_profit     double precision,   -- sum of units_result (real-odds rows only)
  roi_percent      double precision,   -- units_profit / pick_count * 100
  avg_edge         double precision,   -- mean model_edge % (only rows with edge signal)
  avg_win_prob     double precision,   -- mean win-probability % at pick time
  avg_clv          double precision,   -- mean CLV % (pick rows only; null until CLV captured)
  clv_beat_rate    double precision,   -- fraction of picks with beat_close = true
  computed_at      timestamptz
);
