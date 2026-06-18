import re
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


def grade_safe_zone_pick(pick, home, away, home_score, away_score):
    """Grade a safe-zone pick (Over 1.5, Under 3.5, '{Team} or Draw', etc)."""
    total = home_score + away_score
    p = (pick or "").strip()
    pl = p.lower()

    m = re.match(r"^(over|under)\s+(\d+\.?\d*)$", pl)
    if m:
        direction, line = m.group(1), float(m.group(2))
        if direction == "over":
            return "WIN" if total > line else "LOSS"
        return "WIN" if total < line else "LOSS"

    if pl.endswith(" or draw"):
        team = p[: -len(" or Draw")]
        if home_score > away_score:
            actual_winner = home
        elif away_score > home_score:
            actual_winner = away
        else:
            actual_winner = "Draw"
        return "WIN" if actual_winner == "Draw" or actual_winner == team else "LOSS"

    # "Double Chance" alone — can't grade without knowing which double chance was intended
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

    for p in picks:  # noqa: E501 — sharp picks from dashboard view
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

        raw_odds = p.get("odds_decimal")
        odds = num(raw_odds, None)
        no_odds = odds is None or odds <= 1.0
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
            "no_odds": no_odds,
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

    # === Safe Zone picks (balanced + banker) ===
    safe_zone = supabase.table("soccer_safe_zone").select("*").execute().data

    for sz in safe_zone:
        game = game_map.get(sz["game_id"])
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

        home = sz.get("home_team_name", "")
        away = sz.get("away_team_name", "")
        actual_winner = (
            home if home_score > away_score
            else away if away_score > home_score
            else "Draw"
        )

        common = {
            "game_id": sz["game_id"],
            "home_team_name": home,
            "away_team_name": away,
            "publish_status": None,
            "elite_tier": None,
            "confidence": None,
            "elite_score": None,
            "safety_score": None,
            "odds_decimal": None,
            "no_odds": True,
            "closing_odds": None,
            "clv_percent": None,
            "home_score": home_score,
            "away_score": away_score,
            "total_goals": home_score + away_score,
            "btts": home_score > 0 and away_score > 0,
            "winner": actual_winner,
            "graded_at": datetime.now(timezone.utc).isoformat(),
            "raw_result": raw,
        }

        for market_label, pick_val in [
            ("safe_balanced", sz.get("balanced_pick")),
            ("safe_banker", sz.get("banker_pick")),
        ]:
            if not pick_val:
                continue

            grade = grade_safe_zone_pick(pick_val, home, away, home_score, away_score)
            # Wins break even (no odds stored); losses still cost 1 unit
            units = -1.0 if grade == "LOSS" else 0.0

            out = {
                **common,
                "market": market_label,
                "pick": pick_val,
                "grade": grade,
                "units_result": units,
                "roi_percent": round(units * 100, 2),
            }

            supabase.table("soccer_pick_grades_v2").upsert(
                out, on_conflict="game_id,market,pick"
            ).execute()

            print(
                f'{home} vs {away} | [{market_label}] {pick_val} | '
                f'{home_score}-{away_score} | {grade}'
            )
            saved += 1

    print(f"✅ Soccer picks graded: {saved}")


if __name__ == "__main__":
    main()
