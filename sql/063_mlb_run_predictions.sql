create table if not exists mlb_run_predictions (
    id uuid primary key default gen_random_uuid(),

    game_id uuid,
    model_version text default 'poisson_v1',

    home_team_name text,
    away_team_name text,

    expected_home_runs numeric,
    expected_away_runs numeric,
    expected_total_runs numeric,

    -- moneyline (%)
    home_win_probability numeric,
    away_win_probability numeric,

    -- totals (%)
    over_75_probability numeric,
    over_85_probability numeric,
    over_95_probability numeric,
    under_75_probability numeric,
    under_85_probability numeric,
    under_95_probability numeric,

    -- run line: home perspective (diff = home - away)
    home_rl_minus15_prob numeric,  -- P(home wins by 2+), i.e. home -1.5 covers
    home_rl_plus15_prob  numeric,  -- P(home wins OR loses by 1), i.e. home +1.5 covers
    home_rl_plus25_prob  numeric,  -- P(home wins OR loses by <=2), i.e. home +2.5 covers

    -- run line: away perspective
    away_rl_minus15_prob numeric,  -- P(away wins by 2+)
    away_rl_plus15_prob  numeric,  -- P(away wins OR loses by 1)
    away_rl_plus25_prob  numeric,  -- P(away wins OR loses by <=2)

    created_at timestamptz default now(),
    unique(game_id, model_version)
);

create index if not exists idx_mlb_run_pred_game on mlb_run_predictions(game_id);
