-- Dashboard view consumed by grade_soccer_picks.py.
-- Primary source: final_pro_soccer_pick_history (stores pick-time odds after 059 migration).
-- Joined to soccer_master_picks for elite_score / confidence / publish_status columns.
-- DISTINCT ON de-duplicates to one row per game+market+pick (latest run_date wins).

create or replace view soccer_pick_dashboard_view as
with latest_history as (
    select distinct on (game_id, market, pick)
        game_id,
        home_team_name,
        away_team_name,
        market,
        pick,
        odds_decimal,
        no_odds,
        pick_run_date
    from final_pro_soccer_pick_history
    order by game_id, market, pick, pick_run_date desc
),
latest_master as (
    select distinct on (game_id, market, pick)
        game_id,
        market,
        pick,
        publish_status,
        elite_tier,
        confidence,
        elite_score,
        safety_score        as safety_score_v3,
        odds_decimal        as master_odds_decimal
    from soccer_master_picks
    order by game_id, market, pick, run_date desc
)
select
    h.game_id,
    h.home_team_name,
    h.away_team_name,
    h.market,
    h.pick,
    m.publish_status,
    m.elite_tier,
    m.confidence,
    m.elite_score,
    m.safety_score_v3,
    -- prefer pick-time odds stored at publication; fall back to master-picks snapshot
    coalesce(h.odds_decimal, m.master_odds_decimal) as odds_decimal
from latest_history h
left join latest_master m
    on  m.game_id = h.game_id
    and m.market  = h.market
    and m.pick    = h.pick;
