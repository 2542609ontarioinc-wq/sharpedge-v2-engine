from datetime import date, datetime
from zoneinfo import ZoneInfo

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
TORONTO = ZoneInfo("America/Toronto")


def parse_game_datetime(game_row):
    candidates = [
        game_row.get("start_time"),
        game_row.get("commence_time"),
        game_row.get("game_time"),
        game_row.get("fixture_date"),
        game_row.get("date"),
        game_row.get("kickoff"),
        game_row.get("scheduled"),
        game_row.get("start_at"),
        game_row.get("starts_at"),
    ]

    raw = game_row.get("raw_json") or {}
    fixture = raw.get("fixture") or {}

    candidates.append(fixture.get("date"))
    candidates.append(raw.get("date"))

    for value in candidates:
        if not value:
            continue

        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))

            return dt.astimezone(TORONTO)
        except Exception:
            pass

    timestamp = fixture.get("timestamp")
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp), tz=ZoneInfo("UTC")).astimezone(TORONTO)
        except Exception:
            pass

    return None


def build_explanation(row):
    parts = [
        f"Pick is rated {row.get('final_tier')}.",
        f"Final value score: {row.get('final_value_rating')}.",
        f"Safety score: {row.get('safety_score')}.",
        f"Matchup score: {row.get('matchup_score')}.",
    ]

    if row.get("notes"):
        parts.append(f"Notes: {row.get('notes')}.")

    return " ".join(parts)


def main():
    rows = (
        supabase.table("soccer_calibrated_value")
        .select("*")
        .eq("final_allowed", True)
        .order("final_value_rating", desc=True)
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

    today_toronto = datetime.now(TORONTO).date()
    today_iso = today_toronto.isoformat()

    # Clear only CURRENT frontend table.
    # History table is NOT deleted.
    supabase.table("final_pro_soccer_picks").delete().neq(
        "game_id",
        "00000000-0000-0000-0000-000000000000",
    ).execute()

    current_saved = 0
    history_saved = 0
    skipped_past = 0
    skipped_no_date = 0

    for row in rows:
        game_id = row["game_id"]
        game_row = game_map.get(game_id, {})

        game_dt = parse_game_datetime(game_row)
        game_date = game_dt.date().isoformat() if game_dt else None

        out = {
            "game_id": game_id,
            "home_team_name": row["home_team_name"],
            "away_team_name": row["away_team_name"],
            "pick": row["pick"],
            "market": row["market"],
            "bookmaker": row["bookmaker"],
            "final_value_rating": row["final_value_rating"],
            "final_tier": row["final_tier"],
            "raw_value_rating": row["raw_value_rating"],
            "safety_score": row["safety_score"],
            "matchup_score": row["matchup_score"],
            "final_allowed": row["final_allowed"],
            "explanation": build_explanation(row),
            "game_date": game_date,
            "pick_run_date": today_iso,
        }

        # Always save to history for analytics.
        supabase.table("final_pro_soccer_pick_history").upsert(
            out,
            on_conflict="game_id,pick_run_date,market,pick",
        ).execute()
        history_saved += 1

        # Current frontend only shows today/upcoming Toronto games.
        if not game_dt:
            skipped_no_date += 1
            continue

        if game_dt.date() < today_toronto:
            skipped_past += 1
            continue

        supabase.table("final_pro_soccer_picks").upsert(
            out,
            on_conflict="game_id",
        ).execute()
        current_saved += 1

    print(f"✅ Final pro soccer current picks saved: {current_saved}")
    print(f"✅ Final pro soccer history rows saved: {history_saved}")
    print(f"⏭️ Skipped past games: {skipped_past}")
    print(f"⚠️ Skipped no-date games: {skipped_no_date}")
    print(f"📅 Toronto today: {today_iso}")


if __name__ == "__main__":
    main()
    