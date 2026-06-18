create or replace view soccer_api_ready_view as
select
    fp.game_id,

    fp.home_team_name,
    fp.away_team_name,

    fp.pick,
    fp.market,
    fp.bookmaker,

    fp.final_value_rating,
    fp.final_tier,

    fp.safety_score,
    fp.matchup_score,

    mf.best_confidence,
    mf.model_edge,
    mf.data_quality_score,

    mf.temperature_c,
    mf.wind_kph,
    mf.precipitation_mm,

    mf.home_style_label,
    mf.away_style_label,

    mf.home_adjusted_attack_index,
    mf.away_adjusted_attack_index,

    mf.home_adjusted_defense_index,
    mf.away_adjusted_defense_index,

    fp.explanation,
    fp.created_at

from final_pro_soccer_picks fp
left join soccer_match_features mf
on fp.game_id = mf.game_id
where fp.final_allowed = true;