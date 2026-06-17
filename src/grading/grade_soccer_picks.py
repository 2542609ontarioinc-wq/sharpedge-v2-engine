from datetime import datetime, timezone
from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def num(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def grade_pick(market, pick, home, away, home_score, away_score):
    total = home_score + away_score
    btts = home_score > 0 and away_score > 0

    if home_score > away_score:
        winner = home
    elif away_score > home_score:
        winner = away
    else:
        winner = "Draw"

    p = (pick or "").lower()
    m = (market or "").lower()

    if m == "goals":
        if "over 2.5" in p:
            return "WIN" if total > 2.5 else "LOSS"
        if "under 2.5" in p:
            return "WIN" if total < 2.5 else "LOSS"

    if m == "btts":
        if "yes" in p:
            return "WIN" if btts else "LOSS"
        if "no" in p:
            return "WIN" if not btts else "LOSS"

    if m == "winner":
        return "WIN" if pick == winner else "LOSS"

    return "VOID"


def units_result(grade, odds_decimal):
    odds = num(odds_decimal, None)

    if odds is None or odds <= 1:
        return 0

    if grade == "WIN":
        return round(odds - 1, 2)
    if grade == "LOSS":
        return -1
    return 0


def main():
    picks = (
        supabase.table("soccer_pick_dashboard_view")
        .select("*")
        .execute()
        .data
    )

    games = (
        supabase.table("games")
        .select("*")
        .eq("sport_key", "soccer")
        .execute()
        .data
    )

    game_map = {g["id"]: g for g in games}
    saved = 0

    for p in picks:
        game = game_map.get(p["game_id"])
        if not game:
            continue

        raw = game.get("raw_json") or {}
        fixture = raw.get("fixture") or {}
        goals = raw.get("goals") or {}
        status = fixture.get("status") or {}
        short = status.get("short")

        if short not in ["FT", "AET", "PEN"]:
            continue

        home_score = goals.get("home")
        away_score = goals.get("away")

        if home_score is None or away_score is None:
            continue

        home_score = int(home_score)
        away_score = int(away_score)

        grade = grade_pick(
            p.get("market"),
            p.get("pick"),
            p.get("home_team_name"),
            p.get("away_team_name"),
            home_score,
            away_score,
        )

        odds = num(p.get("odds_decimal"), 0)
        units = units_result(grade, odds)

        clv_rows = (
            supabase.table("soccer_closing_line_value")
            .select("*")
            .eq("game_id", p["game_id"])
            .eq("market", p["market"])
            .eq("pick", p["pick"])
            .limit(1)
            .execute()
            .data
        )

        clv = clv_rows[0] if clv_rows else {}

        out = {
            "game_id": p["game_id"],
            "home_team_name": p.get("home_team_name"),
            "away_team_name": p.get("away_team_name"),
            "market": p.get("market"),
            "pick": p.get("pick"),
            "publish_status": p.get("publish_status"),
            "elite_tier": p.get("elite_tier"),
            "confidence": p.get("confidence"),
            "elite_score": p.get("elite_score"),
            "safety_score": p.get("safety_score_v3"),
            "odds_decimal": p.get("odds_decimal"),
            "closing_odds": clv.get("closing_odds"),
            "clv_percent": clv.get("clv_percent"),
            "home_score": home_score,
            "away_score": away_score,
            "total_goals": home_score + away_score,
            "btts": home_score > 0 and away_score > 0,
            "winner": (
                p.get("home_team_name") if home_score > away_score
                else p.get("away_team_name") if away_score > home_score
                else "Draw"
            ),
            "grade": grade,
            "units_result": units,
            "roi_percent": round(units * 100, 2),
            "graded_at": datetime.now(timezone.utc).isoformat(),
            "raw_result": raw,
        }

        supabase.table("soccer_pick_grades_v2").upsert(
            out,
            on_conflict="game_id,market,pick",
        ).execute()

        print(
            f'{p["home_team_name"]} vs {p["away_team_name"]} | '
            f'{p["pick"]} | {home_score}-{away_score} | {grade} | Units {units}'
        )

        saved += 1

    print(f"✅ Soccer picks graded: {saved}")


if __name__ == "__main__":
    main()
