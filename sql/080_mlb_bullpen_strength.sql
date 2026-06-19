-- MLB team bullpen (relief pitching) aggregate strength, keyed by team + season.
-- Populated by src/ingestion/sync_mlb_bullpen.py (one free MLB Stats API call/run).
-- Used by generate_mlb_run_predictions.py model_version='poisson_v3_bullpen' only;
-- the production v2 model is unaffected until backtest confirms improvement.

create table if not exists mlb_bullpen_strength (
    id                 bigserial primary key,
    team_name          text      not null,
    team_mlb_id        integer,
    season             integer   not null,
    bullpen_ip         numeric,          -- total relief innings pitched this season
    bullpen_era        numeric,          -- earned runs per 9 IP
    bullpen_whip       numeric,          -- (BB + H) / IP
    bullpen_k9         numeric,          -- strikeouts per 9 IP
    bullpen_ra9        numeric,          -- runs (earned + unearned) per 9 IP
    raw_ra9_index      numeric,          -- bullpen_ra9 / league_avg_bullpen_ra9
    shrunk_ra9_index   numeric,          -- shrunk toward 1.0 (league avg) via IP-weighted shrinkage
    games_counted      integer,          -- total relief appearances aggregated
    updated_at         timestamptz default now(),
    unique(team_name, season)
);
