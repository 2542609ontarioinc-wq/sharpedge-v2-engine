from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def expected_goals(form_score):
    if form_score >= 90:
        return 2.2
    if form_score >= 75:
        return 1.9
    if form_score >= 60:
        return 1.6
    if form_score >= 45:
        return 1.3
    if form_score >= 30:
        return 1.0
    return 0.8


def main():
    rows = (
        supabase.table("soccer_match_strength")
        .select("*")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data
    )

    saved = 0

    for row in rows:

        home_form = float(row["home_form_score"])
        away_form = float(row["away_form_score"])

        home_xg = expected_goals(home_form)
        away_xg = expected_goals(away_form)

        total = round(home_xg + away_xg, 2)

        if total >= 3.5:
            over25 = 72
        elif total >= 3.0:
            over25 = 64
        elif total >= 2.5:
            over25 = 55
        else:
            over25 = 42

        under25 = 100 - over25

        if home_xg >= 1.2 and away_xg >= 1.2:
            btts_yes = 65
        elif home_xg >= 1.0 and away_xg >= 1.0:
            btts_yes = 58
        else:
            btts_yes = 42

        btts_no = 100 - btts_yes

        prediction = {
            "game_id": row["game_id"],
            "home_team_name": row["home_team_name"],
            "away_team_name": row["away_team_name"],
            "expected_home_goals": home_xg,
            "expected_away_goals": away_xg,
            "expected_total_goals": total,
            "over_25_probability": over25,
            "under_25_probability": under25,
            "btts_yes_probability": btts_yes,
            "btts_no_probability": btts_no,
        }

        supabase.table("soccer_goal_predictions").insert(prediction).execute()
        saved += 1

    print(f"✅ Goal predictions created: {saved}")


if __name__ == "__main__":
    main()
    
    