from datetime import date, datetime
from zoneinfo import ZoneInfo

from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
TORONTO = ZoneInfo("America/Toronto")

TIER_BOD = "Bet of the Day"
TIER_ELITE = "Elite"
TIER_STANDARD = "Standard"
# rank 1 = Bet of the Day; ranks 2–6 = Elite; rest = Standard
ELITE_CUTOFF = 6


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


def _num(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _confidence_sort_key(out_row, pred_map):
    """Sort key: (calibrated_confidence, real_edge_or_0).
    Edge only counts as tiebreaker when the prediction has real odds backing it."""
    pred = pred_map.get(out_row["game_id"])
    if not pred:
        return (0.0, 0.0)
    conf = _num(pred.get("confidence"))
    edge = _num(pred.get("model_edge"))
    # mirror apply_honest_calibration REAL band; edge is only a valid tiebreaker
    # when the pick has odds and the edge is in the sane [-10, 15] range
    has_real_odds = bool(
        pred.get("bookmaker")
        and pred.get("odds_decimal") is not None
        and -10 <= edge <= 15
    )
    return (conf, edge if has_real_odds else 0.0)


def _assign_confidence_tiers(all_out, pred_map):
    """Sort all picks by calibrated confidence (+ real edge tiebreaker) and label tiers."""
    all_out.sort(key=lambda r: _confidence_sort_key(r, pred_map), reverse=True)
    for i, out in enumerate(all_out):
        if i == 0:
            out["confidence_tier"] = TIER_BOD
        elif i < ELITE_CUTOFF:
            out["confidence_tier"] = TIER_ELITE
        else:
            out["confidence_tier"] = TIER_STANDARD


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

    features = (
        supabase.table("soccer_match_features")
        .select("game_id,odds_decimal,bookmaker")
        .execute()
        .data
    )

    # Fetch calibrated predictions for confidence ranking
    predictions = (
        supabase.table("final_soccer_predictions")
        .select("game_id,market,best_pick,confidence,model_edge,bookmaker,odds_decimal")
        .execute()
        .data
    )

    game_map = {g["id"]: g for g in games}
    features_map = {f["game_id"]: f for f in features}

    # Build pred_map: game_id -> best prediction row for this pick.
    # soccer_calibrated_value is one pick per game, so we keep the highest-confidence
    # prediction per game as the confidence reference.
    pred_map = {}
    for p in predictions:
        gid = p["game_id"]
        existing = pred_map.get(gid)
        if existing is None or _num(p.get("confidence")) > _num(existing.get("confidence")):
            pred_map[gid] = p

    today_toronto = datetime.now(TORONTO).date()
    today_iso = today_toronto.isoformat()

    # Clear only CURRENT frontend table.
    # History table is NOT deleted.
    supabase.table("final_pro_soccer_picks").delete().neq(
        "game_id",
        "00000000-0000-0000-0000-000000000000",
    ).execute()

    # --- Pass 1: build all out rows (no tier yet) ---
    all_out = []
    game_datetimes = {}  # game_id -> datetime | None

    for row in rows:
        game_id = row["game_id"]
        game_row = game_map.get(game_id, {})

        game_dt = parse_game_datetime(game_row)
        game_datetimes[game_id] = game_dt
        game_date = game_dt.date().isoformat() if game_dt else None

        feat = features_map.get(game_id, {})
        odds_decimal = feat.get("odds_decimal")

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
            "odds_decimal": odds_decimal,
            "no_odds": odds_decimal is None,
            "confidence_tier": TIER_STANDARD,  # default; overwritten below
        }
        all_out.append(out)

    # --- Pass 2: assign confidence tiers across the full slate ---
    _assign_confidence_tiers(all_out, pred_map)

    # --- Pass 3: upsert ---
    current_saved = 0
    history_saved = 0
    skipped_past = 0
    skipped_no_date = 0

    for out in all_out:
        game_id = out["game_id"]
        game_dt = game_datetimes[game_id]

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
