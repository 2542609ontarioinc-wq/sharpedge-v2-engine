-- Adds pick-time odds columns so grading can compute real profit instead of 0.00u.
-- Run on Supabase before deploying the Python changes that write these columns.

alter table final_pro_soccer_picks
    add column if not exists odds_decimal numeric,
    add column if not exists no_odds      boolean not null default false;

-- final_pro_soccer_pick_history was created without odds columns; add them.
-- The CREATE TABLE below is a no-op if the table already exists; the ALTER adds
-- the missing columns to any existing table.
create table if not exists final_pro_soccer_pick_history (
    id                 uuid        primary key default gen_random_uuid(),
    game_id            uuid        not null,
    pick_run_date      date        not null,
    market             text        not null,
    pick               text        not null,
    home_team_name     text,
    away_team_name     text,
    bookmaker          text,
    final_value_rating numeric,
    final_tier         text,
    raw_value_rating   numeric,
    safety_score       numeric,
    matchup_score      numeric,
    final_allowed      boolean     default false,
    explanation        text,
    game_date          date,
    odds_decimal       numeric,
    no_odds            boolean     not null default false,
    created_at         timestamptz default now(),
    unique (game_id, pick_run_date, market, pick)
);

alter table final_pro_soccer_pick_history
    add column if not exists odds_decimal numeric,
    add column if not exists no_odds      boolean not null default false;

-- Per-pick grade rows gain a no_odds flag so the UI can label 0.00u wins honestly.
alter table soccer_pick_grades_v2
    add column if not exists no_odds boolean not null default false;
