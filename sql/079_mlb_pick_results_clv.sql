-- Add CLV summary columns to the per-market track record.
--
-- avg_clv            : mean CLV across picks with computable CLV (in probability percentage points)
-- clv_positive_count : how many picks beat the closing line
-- clv_sample_size    : denominator — picks with both opening + closing novig available
--
-- Picks without a closing snapshot (alternate-line safe-zone picks, early-season
-- no-odds games) are excluded from all three columns, not counted as 0.
alter table mlb_pick_results
    add column if not exists avg_clv             numeric,
    add column if not exists clv_positive_count  integer default 0,
    add column if not exists clv_sample_size     integer default 0;
