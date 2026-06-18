from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def latest_by_game(table):
    rows = (
        supabase.table(table)
        .select("*")
        .order("created_at", desc=True)
        .limit(5000)
        .execute()
        .data
    )

    out = {}

    for row in rows:
        game_id = row.get("game_id")

        if game_id and game_id not in out:
            out[game_id] = row

    return out


def by_team(table):
    rows = (
        supabase.table(table)
        .select("*")
        .execute()
        .data
    )

    return {row["team_name"]: row for row in rows}


def by_league(table):
    rows = (
        supabase.table(table)
        .select("*")
        .execute()
        .data
    )

    return {str(row["league_id"]): row for row in rows}


def main():
    features = (
        supabase.table("soccer_match_features")
        .select("*")
        .limit(5000)
        .execute()
        .data
    )

    opponent_strength = by_team("soccer_opponent_strength")
    styles = by_team("soccer_team_style_profiles")
    leagues = by_league("soccer_league_baselines")
    rest = latest_by_game("soccer_rest_travel_features")
    weather = latest_by_game("soccer_weather_features")

    updated = 0

    for row in features:
        game_id = row["game_id"]
        home = row["home_team_name"]
        away = row["away_team_name"]
        league_key = str(row.get("league_key"))

        home_opp = opponent_strength.get(home)
        away_opp = opponent_strength.get(away)

        home_style = styles.get(home)
        away_style = styles.get(away)

        league = leagues.get(league_key)
        rest_row = rest.get(game_id)
        weather_row = weather.get(game_id)

        update = {
            "opponent_strength_of_schedule": (
                round(
                    (
                        float(home_opp.get("strength_of_schedule") or 0)
                        + float(away_opp.get("strength_of_schedule") or 0)
                    )
                    / 2,
                    2,
                )
                if home_opp and away_opp
                else None
            ),

            "home_adjusted_attack_index": home_opp.get("adjusted_attack_index") if home_opp else None,
            "away_adjusted_attack_index": away_opp.get("adjusted_attack_index") if away_opp else None,
            "home_adjusted_defense_index": home_opp.get("adjusted_defense_index") if home_opp else None,
            "away_adjusted_defense_index": away_opp.get("adjusted_defense_index") if away_opp else None,

            "home_style_label": home_style.get("style_label") if home_style else None,
            "away_style_label": away_style.get("style_label") if away_style else None,
            "home_high_card_risk": home_style.get("high_card_risk") if home_style else False,
            "away_high_card_risk": away_style.get("high_card_risk") if away_style else False,
            "home_high_corner_team": home_style.get("high_corner_team") if home_style else False,
            "away_high_corner_team": away_style.get("high_corner_team") if away_style else False,

            "league_avg_goals": league.get("avg_goals") if league else None,
            "league_avg_corners": league.get("avg_corners") if league else None,
            "league_avg_yellow_cards": league.get("avg_yellow_cards") if league else None,
            "league_btts_rate": league.get("btts_rate") if league else None,
            "league_over_25_rate": league.get("over_25_rate") if league else None,

            "home_days_rest": rest_row.get("home_days_rest") if rest_row else None,
            "away_days_rest": rest_row.get("away_days_rest") if rest_row else None,
            "rest_advantage": rest_row.get("rest_advantage") if rest_row else None,
            "congestion_score": rest_row.get("congestion_score") if rest_row else None,

            "venue_name": weather_row.get("venue_name") if weather_row else None,
            "venue_city": weather_row.get("venue_city") if weather_row else None,
            "temperature_c": weather_row.get("temperature_c") if weather_row else None,
            "wind_kph": weather_row.get("wind_kph") if weather_row else None,
            "precipitation_mm": weather_row.get("precipitation_mm") if weather_row else None,
            "weather_risk_score": weather_row.get("weather_risk_score") if weather_row else None,
            "goals_weather_modifier": weather_row.get("goals_weather_modifier") if weather_row else None,
            "corners_weather_modifier": weather_row.get("corners_weather_modifier") if weather_row else None,
        }

        supabase.table("soccer_match_features").update(update).eq(
            "game_id",
            game_id,
        ).execute()

        updated += 1

    print(f"✅ Pro match features updated: {updated}")


if __name__ == "__main__":
    main()