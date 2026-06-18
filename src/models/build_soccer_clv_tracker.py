from collections import defaultdict
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


def parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def clv_for_over_like(opening, closing):
    if not opening or not closing:
        return None
    return round(((opening - closing) / opening) * 100, 2)


def main():
    snapshots = (
        supabase.table("soccer_live_odds_snapshots")
        .select("*")
        .order("captured_at", desc=False)
        .execute()
        .data
    )

    grouped = defaultdict(list)

    for s in snapshots:
        key = (
            s.get("game_id"),
            s.get("market"),
            s.get("pick"),
            s.get("bookmaker"),
        )
        grouped[key].append(s)

    saved = 0

    for (game_id, market, pick, bookmaker), rows in grouped.items():
        rows = [r for r in rows if r.get("odds_decimal")]
        if not rows:
            continue

        rows.sort(key=lambda r: parse_dt(r.get("captured_at")) or datetime.min.replace(tzinfo=timezone.utc))

        opening = rows[0]
        latest = rows[-1]

        opening_odds = num(opening.get("odds_decimal"))
        latest_odds = num(latest.get("odds_decimal"))

        # For now, latest snapshot acts as closing estimate.
        # Later, after kickoff/final, this becomes true closing snapshot.
        closing = latest
        closing_odds = latest_odds

        clv_percent = clv_for_over_like(opening_odds, closing_odds)
        beat = clv_percent is not None and clv_percent > 0

        out = {
            "game_id": game_id,
            "market": market,
            "pick": pick,
            "bookmaker": bookmaker,
            "opening_odds": opening_odds,
            "latest_odds": latest_odds,
            "closing_odds": closing_odds,
            "opening_time": opening.get("captured_at"),
            "latest_time": latest.get("captured_at"),
            "closing_time": closing.get("captured_at"),
            "clv_percent": clv_percent,
            "beat_closing_line": beat,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        supabase.table("soccer_closing_line_value").upsert(
            out,
            on_conflict="game_id,market,pick",
        ).execute()

        saved += 1

    print(f"✅ Soccer CLV tracker rows upserted: {saved}")


if __name__ == "__main__":
    main()
