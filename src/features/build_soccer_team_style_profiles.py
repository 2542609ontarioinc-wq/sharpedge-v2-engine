from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def choose_label(profile):
    if profile["high_press_style"] and profile["high_tempo_style"]:
        return "High Press / High Tempo"

    if profile["possession_style"]:
        return "Possession"

    if profile["direct_style"]:
        return "Direct / Transition"

    if profile["defensive_style"]:
        return "Defensive"

    if profile["high_corner_team"]:
        return "Wide / Corner Pressure"

    return "Balanced"


def main():
    rows = (
        supabase.table("soccer_team_advanced_rolling_features")
        .select("*")
        .execute()
        .data
    )

    saved = 0

    for row in rows:
        possession_style = float(row["weighted_possession"] or 0) >= 55
        high_press_style = float(row["defense_index"] or 0) >= 55
        direct_style = (
            float(row["weighted_possession"] or 0) < 48
            and float(row["attack_index"] or 0) >= 100
        )
        crossing_style = float(row["corners_index"] or 0) >= 80
        defensive_style = float(row["defense_index"] or 0) >= 65
        high_tempo_style = float(row["weighted_shots_total"] or 0) >= 14
        high_card_risk = float(row["cards_index"] or 0) >= 65
        high_corner_team = float(row["corners_index"] or 0) >= 85

        profile = {
            "team_name": row["team_name"],

            "possession_style": possession_style,
            "high_press_style": high_press_style,
            "direct_style": direct_style,
            "crossing_style": crossing_style,
            "defensive_style": defensive_style,
            "high_tempo_style": high_tempo_style,
            "high_card_risk": high_card_risk,
            "high_corner_team": high_corner_team,

            "attack_index": row["attack_index"],
            "defense_index": row["defense_index"],
            "cards_index": row["cards_index"],
            "corners_index": row["corners_index"],
        }

        profile["style_label"] = choose_label(profile)

        supabase.table("soccer_team_style_profiles").upsert(
            profile,
            on_conflict="team_name",
        ).execute()

        saved += 1

    print(f"✅ Team style profiles upserted: {saved}")


if __name__ == "__main__":
    main()