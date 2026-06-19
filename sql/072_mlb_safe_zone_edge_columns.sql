-- Add no-vig edge columns to mlb_safe_zone so balanced/banker picks can show
-- real market edge (REAL/suspect) instead of no-odds when alternate-line odds exist.

alter table mlb_safe_zone
    add column if not exists balanced_novig_pct  numeric,
    add column if not exists balanced_edge        numeric,
    add column if not exists balanced_edge_flag   text,   -- 'REAL', 'suspect', 'no-odds'
    add column if not exists banker_novig_pct     numeric,
    add column if not exists banker_edge          numeric,
    add column if not exists banker_edge_flag     text;
