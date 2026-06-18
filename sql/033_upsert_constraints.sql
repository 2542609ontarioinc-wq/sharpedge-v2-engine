create unique index if not exists ux_final_soccer_predictions_game_market
on final_soccer_predictions (game_id, market);

create unique index if not exists ux_soccer_ensemble_predictions_game
on soccer_ensemble_predictions (game_id);

create unique index if not exists ux_soccer_premium_rankings_game
on soccer_premium_rankings (game_id);

create unique index if not exists ux_soccer_data_quality_gate_game
on soccer_data_quality_gate (game_id);
