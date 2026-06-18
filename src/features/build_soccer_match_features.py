from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def latest_by_game(rows):
    out = {}

    for row in rows:
        game_id = row.get("game_id")

        if not game_id:
            continue

        if game_id not in out:
            out[game_id] = row

    return out


def latest_form_by_game_team(rows):
    out = {}

    for row in rows:
        game_id = row.get("game_id")
        team_name = row.get("team_name")

        if not game_id or not team_name:
            continue

        key = (game_id, team_name)

        if key not in out:
            out[key] = row

    return out


def fetch_all(table, select="*"):
    return (
        supabase.table(table)
        .select(select)
        .order("created_at", desc=True)
        .limit(5000)
        .execute()
        .data
    )


def main():
    games = (
        supabase.table("games")
        .select("*")
        .eq("sport_key", "soccer")
        .limit(5000)
        .execute()
        .data
    )

    form_rows = fetch_all("soccer_form_features")
    strength_rows = fetch_all("soccer_match_strength")
    goals_rows = fetch_all("soccer_goals_prediction_versions")
    btts_rows = fetch_all("soccer_btts_prediction_versions")
    winner_rows = fetch_all("soccer_prediction_versions")
    final_rows = fetch_all("final_soccer_predictions")
    quality_rows = fetch_all("soccer_data_quality_gate")
    lineup_rows = fetch_all("soccer_lineup_impact")
    injury_rows = fetch_all("soccer_injury_impact")

    forms = latest_form_by_game_team(form_rows)
    strengths = latest_by_game(strength_rows)
    goals_map = latest_by_game(goals_rows)
    btts_map = latest_by_game(btts_rows)
    winners = latest_by_game(winner_rows)
    finals = latest_by_game(final_rows)
    qualities = latest_by_game(quality_rows)
    lineups = latest_by_game(lineup_rows)
    injuries = latest_by_game(injury_rows)

    saved = 0

    for game in games:
        game_id = game["id"]
        raw = game.get("raw_json") or {}
        league = raw.get("league") or {}

        home_name = game["home_team_name"]
        away_name = game["away_team_name"]

        final = finals.get(game_id)

        if not final:
            continue

        home_form = forms.get((game_id, home_name))
        away_form = forms.get((game_id, away_name))
        strength = strengths.get(game_id)
        goals = goals_map.get(game_id)
        btts = btts_map.get(game_id)
        winner = winners.get(game_id)
        quality = qualities.get(game_id)
        lineup = lineups.get(game_id)
        injury = injuries.get(game_id)

        row = {
            "game_id": game_id,
            "league_key": game.get("league_key"),
            "league_name": league.get("name"),
            "country": league.get("country"),
            "season": str(league.get("season")) if league.get("season") else None,
            "round": league.get("round"),
            "game_date": game.get("game_date"),

            "home_team_name": home_name,
            "away_team_name": away_name,

            "home_form_score": home_form.get("form_score") if home_form else None,
            "away_form_score": away_form.get("form_score") if away_form else None,
            "form_difference": strength.get("form_difference") if strength else None,

            "home_goals_for": home_form.get("goals_for") if home_form else None,
            "home_goals_against": home_form.get("goals_against") if home_form else None,
            "away_goals_for": away_form.get("goals_for") if away_form else None,
            "away_goals_against": away_form.get("goals_against") if away_form else None,

            "home_expected_goals": goals.get("expected_home_goals") if goals else None,
            "away_expected_goals": goals.get("expected_away_goals") if goals else None,
            "expected_total_goals": goals.get("expected_total_goals") if goals else None,

            "winner_pick": winner.get("predicted_winner") if winner else None,
            "winner_confidence": winner.get("confidence_score") if winner else None,

            "goals_pick": final.get("best_pick") if final.get("market") == "goals" else None,
            "goals_confidence": final.get("confidence") if final.get("market") == "goals" else None,

            "btts_pick": btts.get("predicted_btts") if btts else None,
            "btts_confidence": btts.get("confidence_score") if btts else None,

            "best_pick": final.get("best_pick"),
            "best_market": final.get("market"),
            "best_confidence": final.get("confidence"),

            "bookmaker": final.get("bookmaker"),
            "odds_decimal": final.get("odds_decimal"),
            "odds_american": final.get("odds_american"),
            "market_implied_probability": final.get("market_implied_probability"),
            "model_edge": final.get("model_edge"),

            "has_form": quality.get("has_form") if quality else False,
            "has_odds": quality.get("has_odds") if quality else False,
            "has_lineup": bool(lineup),
            "has_injury_data": bool(injury),

            "data_quality_score": quality.get("quality_score") if quality else 0,
            "allowed_for_premium": quality.get("allowed_for_premium") if quality else False,
        }

        supabase.table("soccer_match_features").upsert(
            row,
            on_conflict="game_id",
        ).execute()

        saved += 1

    print(f"✅ Soccer match feature rows upserted: {saved}")


if __name__ == "__main__":
    main()
    