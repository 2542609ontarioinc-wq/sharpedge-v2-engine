-- MLB Safe Zone: softer bets derived from the sharp Poisson pick.
--
-- Moneyline sharp pick  → Balanced = team run-line +1.5 | Banker = team +2.5 (prob>=80%)
-- Total OVER  L         → Balanced = Over(L-1)          | Banker = Over(L-2)  (prob>=80%)
-- Total UNDER L         → Balanced = Under(L+1)         | Banker = Under(L+2) (prob>=80%)

create table if not exists mlb_safe_zone (
    id uuid primary key default gen_random_uuid(),

    game_id uuid unique,
    home_team_name text,
    away_team_name text,

    sharp_pick text,
    sharp_market text,
    sharp_edge numeric,

    balanced_pick text,
    balanced_prob numeric,
    balanced_odds_decimal numeric,

    banker_pick text,
    banker_prob numeric,
    banker_odds_decimal numeric,

    updated_at timestamptz default now()
);
