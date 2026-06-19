-- Per-batter hitting-split stats (vs LHP / vs RHP) for today's confirmed lineups.
-- Populated by src/ingestion/sync_mlb_batter_stats.py (free MLB Stats API, ~9 calls/game).
-- Used by generate_mlb_run_predictions.py model_version='poisson_v4_lineup' only;
-- production v2 and shadow v3 are unaffected.

create table if not exists mlb_batter_strength (
    id                  bigserial primary key,
    player_mlb_id       bigint       not null,
    player_name         text,
    game_date           date         not null,
    season              int          not null,
    split               text         not null,  -- 'vL' (vs LHP) or 'vR' (vs RHP)
    at_bats             int,
    hits                int,
    doubles             int,
    triples             int,
    home_runs           int,
    walks               int,
    obp                 numeric,
    slg                 numeric,
    ops                 numeric,
    -- ops_index = ops / league_avg_ops_for_split (raw, before shrinkage)
    ops_index           numeric,
    -- shrunk toward 1.0 (league avg) using K=100 at-bat Bayesian prior
    shrunk_ops_index    numeric,
    -- 0..1, based on min(at_bats, 200)/200 — useful for lineup quality audit
    sample_weight       numeric,
    synced_at           timestamptz  default now(),
    unique(player_mlb_id, game_date, split)
);

create index if not exists mlb_batter_strength_date_idx on mlb_batter_strength(game_date);
create index if not exists mlb_batter_strength_player_idx on mlb_batter_strength(player_mlb_id);
