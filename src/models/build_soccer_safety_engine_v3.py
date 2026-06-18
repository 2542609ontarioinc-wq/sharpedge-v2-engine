from datetime import datetime
from zoneinfo import ZoneInfo

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
TORONTO = ZoneInfo("America/Toronto")


def num(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def gate(name, score, max_score, passed, note):
    return {
        "gate": name,
        "score": round(score, 2),
        "max_score": max_score,
        "passed": passed,
        "note": note,
    }


def score_confidence(row):
    confidence = num(row.get("confidence") or row.get("best_confidence"), 0)

    if confidence >= 78:
        return gate("Confidence", 20, 20, True, "Elite model confidence.")
    if confidence >= 70:
        return gate("Confidence", 16, 20, True, "Strong model confidence.")
    if confidence >= 62:
        return gate("Confidence", 10, 20, False, "Playable confidence, but below safe-pick level.")
    return gate("Confidence", 4, 20, False, "Confidence is too low.")


def score_ev(row):
    edge = num(row.get("model_edge"))
    odds = num(row.get("odds_decimal"))

    if edge is None or odds is None:
        return gate("Expected Value", 0, 15, False, "EV cannot be trusted because odds or edge are missing.")
    if edge >= 12:
        return gate("Expected Value", 15, 15, True, "Excellent positive EV signal.")
    if edge >= 8:
        return gate("Expected Value", 12, 15, True, "Strong positive EV signal.")
    if edge >= 5:
        return gate("Expected Value", 9, 15, True, "Positive EV, but not elite.")
    if edge > 0:
        return gate("Expected Value", 4, 15, False, "Small edge. Not enough EV for safe-pick status.")
    return gate("Expected Value", 0, 15, False, "No positive EV edge.")


def score_edge(row):
    edge = num(row.get("model_edge"))

    if edge is None:
        return gate("Model Edge", 0, 15, False, "Model edge missing.")
    if edge >= 10:
        return gate("Model Edge", 15, 15, True, "Strong model edge over market.")
    if edge >= 6:
        return gate("Model Edge", 11, 15, True, "Good model edge over market.")
    if edge >= 3:
        return gate("Model Edge", 6, 15, False, "Edge exists but is too thin.")
    return gate("Model Edge", 0, 15, False, "No useful edge.")


def score_odds_quality(row):
    odds = num(row.get("odds_decimal"))
    bookmaker = row.get("bookmaker")

    if odds and bookmaker:
        return gate("Odds Quality", 10, 10, True, f"Bookmaker odds confirmed from {bookmaker}.")
    if odds:
        return gate("Odds Quality", 6, 10, False, "Odds exist but bookmaker source missing.")
    return gate("Odds Quality", 0, 10, False, "No matched sportsbook odds.")


def score_weather(row):
    temp = num(row.get("temperature_c"))
    wind = num(row.get("wind_kph"))
    rain = num(row.get("precipitation_mm"))

    if temp is None and wind is None and rain is None:
        return gate("Weather", 3, 5, True, "Weather unavailable; neutral score.")

    penalty = 0
    notes = []

    if wind is not None and wind >= 25:
        penalty += 2
        notes.append("High wind risk.")
    if rain is not None and rain >= 2:
        penalty += 2
        notes.append("Rain risk.")
    if temp is not None and temp >= 33:
        penalty += 1
        notes.append("High heat risk.")

    score = max(0, 5 - penalty)
    return gate("Weather", score, 5, score >= 3, " ".join(notes) if notes else "Weather acceptable.")


def score_injuries(row):
    home_impact = num(row.get("home_injury_impact"), 0)
    away_impact = num(row.get("away_injury_impact"), 0)
    total = abs(home_impact) + abs(away_impact)

    if total >= 20:
        return gate("Injuries", 2, 10, False, "Major injury impact detected.")
    if total >= 10:
        return gate("Injuries", 6, 10, False, "Moderate injury risk.")
    return gate("Injuries", 10, 10, True, "No major injury concern detected.")


def score_lineups(row, lineup_map):
    lineup = lineup_map.get(row["game_id"])

    if lineup:
        home_xi = num(lineup.get("home_confirmed_xi"), 0)
        away_xi = num(lineup.get("away_confirmed_xi"), 0)
        status = lineup.get("lineup_status")

        if home_xi == 11 and away_xi == 11:
            return gate("Lineups", 10, 10, True, "Live lineup confirmed: both teams have starting XI.")
        if status == "partial" or home_xi > 0 or away_xi > 0:
            return gate("Lineups", 5, 10, False, "Live lineup partially available only.")
        return gate("Lineups", 4, 10, False, "Live lineup not available yet.")

    return gate("Lineups", 4, 10, False, "No live lineup row found.")


def score_referee(row):
    strictness = num(row.get("referee_strictness_score"))

    if strictness is None:
        return gate("Referee", 3, 5, True, "Referee data unavailable; neutral score.")
    if strictness >= 145:
        return gate("Referee", 2, 5, False, "Very strict referee may create volatility.")
    if strictness >= 120:
        return gate("Referee", 3, 5, True, "Strict referee but acceptable.")
    return gate("Referee", 5, 5, True, "Referee profile acceptable.")


def score_rest(row):
    home_rest = num(row.get("home_rest_days"))
    away_rest = num(row.get("away_rest_days"))

    if home_rest is None and away_rest is None:
        return gate("Rest", 2, 3, True, "Rest data unavailable; neutral score.")
    if home_rest is not None and home_rest < 3:
        return gate("Rest", 1, 3, False, "Home team has short rest.")
    if away_rest is not None and away_rest < 3:
        return gate("Rest", 1, 3, False, "Away team has short rest.")
    return gate("Rest", 3, 3, True, "Rest situation acceptable.")


def score_travel(row):
    travel = num(row.get("travel_risk_score"))

    if travel is None:
        return gate("Travel", 2, 3, True, "Travel data unavailable; neutral score.")
    if travel >= 8:
        return gate("Travel", 1, 3, False, "High travel risk.")
    if travel >= 5:
        return gate("Travel", 2, 3, True, "Moderate travel risk.")
    return gate("Travel", 3, 3, True, "Travel risk acceptable.")


def score_form(row):
    home_form = num(row.get("home_form_score"))
    away_form = num(row.get("away_form_score"))

    if home_form is None and away_form is None:
        return gate("Team Form", 1, 2, True, "Form data unavailable; neutral score.")
    return gate("Team Form", 2, 2, True, "Form data included.")


def score_league(row):
    league_goals = num(row.get("league_avg_goals"))

    if league_goals is None:
        return gate("League Reliability", 1, 2, True, "League baseline unavailable; neutral score.")
    return gate("League Reliability", 2, 2, True, "League baseline available.")


def build_report(row, lineup_map):
    gates = [
        score_confidence(row),
        score_ev(row),
        score_edge(row),
        score_odds_quality(row),
        score_weather(row),
        score_injuries(row),
        score_lineups(row, lineup_map),
        score_referee(row),
        score_rest(row),
        score_travel(row),
        score_form(row),
        score_league(row),
    ]

    total = round(sum(g["score"] for g in gates), 2)
    failed = [g for g in gates if not g["passed"]]
    passed = [g for g in gates if g["passed"]]

    hard_fail_names = {"Expected Value", "Model Edge", "Odds Quality"}
    hard_failed = any(g["gate"] in hard_fail_names and not g["passed"] for g in gates)

    if total >= 90 and not hard_failed:
        status = "ELITE"
        label = "Elite Pick"
        recommendation = "Publish as premium elite pick."
    elif total >= 78 and not hard_failed:
        status = "SAFE"
        label = "Safe Pick"
        recommendation = "Publish as safe pick."
    elif total >= 60:
        status = "WATCHLIST"
        label = "Watchlist"
        recommendation = "Keep on watchlist. Needs market/safety confirmation."
    else:
        status = "REJECT"
        label = "Reject"
        recommendation = "Do not publish."

    return total, status, label, recommendation, gates, passed, failed


def main():
    safe_rows = supabase.table("soccer_api_ready_view").select("*").execute().data
    watch_rows = supabase.table("soccer_today_watchlist_view").select("*").execute().data
    lineup_rows = supabase.table("soccer_live_lineups").select("*").execute().data

    lineup_map = {r["game_id"]: r for r in lineup_rows}

    combined = {}
    for row in safe_rows:
        combined[row["game_id"]] = row
    for row in watch_rows:
        combined[row["game_id"]] = row

    today = datetime.now(TORONTO).date().isoformat()
    saved = 0

    for row in combined.values():
        total, status, label, recommendation, gates, passed, failed = build_report(row, lineup_map)

        out = {
            "game_id": row["game_id"],
            "home_team_name": row.get("home_team_name"),
            "away_team_name": row.get("away_team_name"),
            "pick": row.get("pick") or row.get("best_pick"),
            "market": row.get("market"),
            "confidence": row.get("best_confidence") or row.get("confidence"),
            "model_edge": row.get("model_edge"),
            "odds_decimal": row.get("odds_decimal"),
            "bookmaker": row.get("bookmaker"),

            "confidence_score": next(g["score"] for g in gates if g["gate"] == "Confidence"),
            "ev_score": next(g["score"] for g in gates if g["gate"] == "Expected Value"),
            "edge_score": next(g["score"] for g in gates if g["gate"] == "Model Edge"),
            "odds_quality_score": next(g["score"] for g in gates if g["gate"] == "Odds Quality"),
            "weather_score": next(g["score"] for g in gates if g["gate"] == "Weather"),
            "injury_score": next(g["score"] for g in gates if g["gate"] == "Injuries"),
            "lineup_score": next(g["score"] for g in gates if g["gate"] == "Lineups"),
            "referee_score": next(g["score"] for g in gates if g["gate"] == "Referee"),
            "rest_score": next(g["score"] for g in gates if g["gate"] == "Rest"),
            "travel_score": next(g["score"] for g in gates if g["gate"] == "Travel"),
            "form_score": next(g["score"] for g in gates if g["gate"] == "Team Form"),
            "league_score": next(g["score"] for g in gates if g["gate"] == "League Reliability"),

            "safety_score_v3": total,
            "safety_status_v3": status,
            "safety_label_v3": label,
            "recommendation_v3": recommendation,

            "failed_gates": failed,
            "passed_gates": passed,
            "gate_report": gates,
            "run_date": today,
        }

        supabase.table("soccer_safety_engine_v3").upsert(
            out,
            on_conflict="game_id,market,pick,run_date",
        ).execute()

        saved += 1

    print(f"✅ Soccer Safety Engine V3 rows upserted: {saved}")


if __name__ == "__main__":
    main()
