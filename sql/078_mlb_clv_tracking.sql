-- Per-pick closing-line value (CLV) for graded MLB game picks.
--
-- CLV = closing_novig_prob - opening_novig_prob
-- Positive CLV: market moved toward our pick after we published it.
-- We de-vig both prices before computing CLV so vig changes don't pollute the signal.
--
-- Excludes: no-odds picks (opening novig unknown), VOID picks, player props.
-- Populated by src/models/build_mlb_clv.py after grading each morning.
create table if not exists mlb_clv_tracking (
    id uuid primary key default gen_random_uuid(),

    game_id uuid not null,
    market text not null,   -- 'moneyline', 'totals', 'run_line', 'safe_balanced', 'safe_banker'
    pick text not null,

    -- Opening: de-vigged implied probability at pick generation time (morning run).
    opening_novig_prob numeric,
    opening_odds_decimal numeric,
    opening_captured_at timestamptz,

    -- Closing: de-vigged implied probability from latest snapshot before game start.
    closing_novig_prob numeric,
    closing_odds_decimal numeric,
    closing_captured_at timestamptz,

    -- CLV = closing_novig_prob - opening_novig_prob (both as percentages, e.g. 52.3).
    clv numeric,
    beat_close boolean,

    computed_at timestamptz default now(),

    unique(game_id, market, pick)
);

create index if not exists idx_mlb_clv_game   on mlb_clv_tracking(game_id);
create index if not exists idx_mlb_clv_market on mlb_clv_tracking(market);
