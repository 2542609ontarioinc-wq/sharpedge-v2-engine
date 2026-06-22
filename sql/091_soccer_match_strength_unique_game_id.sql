-- Add unique constraint on game_id so build_match_strength can upsert
-- instead of insert (which was accumulating duplicates on every pipeline run).
alter table soccer_match_strength
    add constraint if not exists soccer_match_strength_game_id_unique unique (game_id);
