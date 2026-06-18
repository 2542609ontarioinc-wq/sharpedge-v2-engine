from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def num(value, default=0):
    try:
        return float(value)
    except Exception:
        return default


def style_bonus(home_style, away_style):
    home_style = home_style or ""
    away_style = away_style or ""

    bonus = 0
    label = f"{home_style} vs {away_style}"

    if "Elite" in home_style and "Low Block" in away_style:
        bonus += 8

    if "Possession" in home_style and "Physical" in away_style:
        bonus -= 2

    if "Direct" in home_style and "Possession" in away_style:
        bonus += 4

    if "Corner" in home_style and "Defensive" in away_style:
        bonus += 5

    if "Physical" in home_style and "Physical" in away_style:
        bonus -= 3

    return label, bonus


def main():
    rows = (
        supabase.table("soccer_match_features")
        .select("*")
        .limit(5000)
        .execute()
        .data
    )

    saved = 0

    for row in rows:
        game_id = row["game_id"]

        home_attack = num(row.get("home_adjusted_attack_index"))
        away_attack = num(row.get("away_adjusted_attack_index"))
        home_defense = num(row.get("home_adjusted_defense_index"))
        away_defense = num(row.get("away_adjusted_defense_index"))

        attack_edge = round(home_attack - away_defense, 2)
        defense_edge = round(home_defense - away_attack, 2)

        corner_edge = 0
        if row.get("home_high_corner_team"):
            corner_edge += 10
        if row.get("away_high_corner_team"):
            corner_edge -= 10

        card_edge = 0
        if row.get("home_high_card_risk"):
            card_edge += 8
        if row.get("away_high_card_risk"):
            card_edge += 8

        style_matchup, style_score = style_bonus(
            row.get("home_style_label"),
            row.get("away_style_label"),
        )

        possession_advantage = 0
        transition_advantage = 0
        pressing_advantage = 0

        if "Possession" in (row.get("home_style_label") or ""):
            possession_advantage += 5

        if "Direct" in (row.get("home_style_label") or ""):
            transition_advantage += 5

        if "High Press" in (row.get("home_style_label") or ""):
            pressing_advantage += 5

        wind = num(row.get("wind_kph"))
        rain = num(row.get("precipitation_mm"))
        temp = num(row.get("temperature_c"))

        weather_fit = 0

        if wind >= 25:
            weather_fit -= 6

        if rain >= 2:
            weather_fit -= 5

        if temp >= 32:
            weather_fit -= 3

        rest_edge = num(row.get("rest_advantage"))
        congestion = num(row.get("congestion_score"))
        travel_edge = 0

        sos = num(row.get("opponent_strength_of_schedule"))
        sos_edge = round(sos - 75, 2) if sos else 0

        league_goals = num(row.get("league_avg_goals"))
        league_boost = 0
        if league_goals >= 3:
            league_boost += 4

        home_advantage = 5

        tactical_edge = round(
            style_score
            + possession_advantage
            + transition_advantage
            + pressing_advantage
            + league_boost
            + weather_fit
            + rest_edge
            - (congestion * 0.2),
            2,
        )

        overall = round(
            50
            + (attack_edge * 0.12)
            + (defense_edge * 0.08)
            + (corner_edge * 0.3)
            + (card_edge * 0.15)
            + (tactical_edge * 0.5)
            + (sos_edge * 0.1)
            + home_advantage,
            2,
        )

        final = max(0, min(100, overall))

        out = {
            "game_id": game_id,
            "home_team": row["home_team_name"],
            "away_team": row["away_team_name"],
            "attack_edge": attack_edge,
            "defense_edge": defense_edge,
            "corner_edge": corner_edge,
            "card_edge": card_edge,
            "style_matchup": style_matchup,
            "possession_advantage": possession_advantage,
            "transition_advantage": transition_advantage,
            "pressing_advantage": pressing_advantage,
            "referee_fit": 0,
            "weather_fit": weather_fit,
            "rest_edge": rest_edge,
            "travel_edge": travel_edge,
            "sos_edge": sos_edge,
            "home_advantage": home_advantage,
            "tactical_edge": tactical_edge,
            "overall_matchup_score": final,
        }

        supabase.table("soccer_matchup_features").upsert(
            out,
            on_conflict="game_id",
        ).execute()

        saved += 1

    print(f"✅ Soccer matchup features upserted: {saved}")


if __name__ == "__main__":
    main()