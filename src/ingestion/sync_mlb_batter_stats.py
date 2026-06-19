"""
Sync per-batter handedness split stats (vs LHP / vs RHP) for today's confirmed lineups.

Also enriches mlb_pitchers rows with pitch_hand (L/R) when the column is NULL.

Run AFTER sync_mlb_lineups (stage 3) and sync_mlb_pitchers (stage 2) in the daily
MLB engine.  Uses the free MLB Stats API — no key required.

For each confirmed batter in mlb_lineups (today):
  1. Fetch season split stats via /people/{id}/stats?stats=statSplits&sitCodes=vl,vr
  2. Compute shrunk OPS index relative to league average for each split.
  3. Upsert into mlb_batter_strength keyed by (player_mlb_id, game_date, split).

For each pitcher in mlb_pitchers (today) with pitch_hand IS NULL:
  1. Fetch /people/{pitcher_mlb_id} to get pitchHand.code.
  2. Update mlb_pitchers.pitch_hand.

The v4 lineup model in generate_mlb_run_predictions.py reads from both tables.
API cost: ~9 split-stat calls/game + 2 pitcher-hand calls/game (~168 calls for 15 games).
"""
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from supabase import create_client

from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

TORONTO = ZoneInfo("America/Toronto")
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# League-average OPS by pitcher handedness (2024 MLB season)
LEAGUE_AVG_OPS = {"vL": 0.692, "vR": 0.710}
# Bayesian shrinkage prior weight in at-bats; K=100 means 50% prior at 100 AB
SHRINK_K = 100


def _safe(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _fetch_split_stats(player_id, season):
    """Return dict of {split_code: stat_dict} for vl and vr, or {} on no data."""
    r = requests.get(
        f"{MLB_API_BASE}/people/{player_id}/stats",
        params={
            "stats": "statSplits",
            "group": "hitting",
            "season": season,
            "sitCodes": "vl,vr",
        },
        timeout=15,
    )
    r.raise_for_status()
    result = {}
    for group in r.json().get("stats", []):
        for split in group.get("splits", []):
            code = (split.get("split") or {}).get("code", "")
            if code in ("vl", "vr"):
                result[code] = split.get("stat", {})
    return result


def _fetch_pitcher_hand(pitcher_mlb_id):
    """Return pitchHand code ('L', 'R', 'S') or None."""
    r = requests.get(
        f"{MLB_API_BASE}/people/{pitcher_mlb_id}",
        timeout=15,
    )
    r.raise_for_status()
    people = r.json().get("people", [])
    if people:
        return (people[0].get("pitchHand") or {}).get("code")
    return None


def _shrunk_ops_index(stat, split_key):
    """
    Return (raw_ops_index, shrunk_ops_index, sample_weight) or (None, None, 0).

    raw_index = ops / league_avg_ops[split]
    shrunk    = (AB * raw + K * 1.0) / (AB + K)   [Bayesian shrink toward 1.0]
    """
    ops = _safe(stat.get("ops"), default=None)
    at_bats = _safe(stat.get("atBats"), default=0)
    if ops is None or at_bats < 1:
        return None, None, 0.0
    league_avg = LEAGUE_AVG_OPS.get(split_key, 0.700)
    raw_index = ops / league_avg
    shrunk = (at_bats * raw_index + SHRINK_K * 1.0) / (at_bats + SHRINK_K)
    sample_weight = round(min(at_bats, 200) / 200, 3)
    return round(raw_index, 4), round(shrunk, 4), sample_weight


def _enrich_pitcher_hands(today):
    """Populate pitch_hand on mlb_pitchers rows that are missing it (today + yesterday)."""
    rows = (
        supabase.table("mlb_pitchers")
        .select("id,pitcher_mlb_id,pitcher_name,pitch_hand")
        .gte("game_date", (today - timedelta(days=1)).isoformat())
        .execute()
        .data
    )
    updated = 0
    for r in rows:
        if r.get("pitch_hand"):
            continue
        pid = r.get("pitcher_mlb_id")
        if not pid:
            continue
        try:
            hand = _fetch_pitcher_hand(pid)
            time.sleep(0.05)
        except Exception as e:
            print(f"  pitcher hand fetch failed for {r.get('pitcher_name')}: {e}")
            continue
        if hand:
            supabase.table("mlb_pitchers").update({"pitch_hand": hand}).eq("id", r["id"]).execute()
            updated += 1
    return updated


def main():
    today = datetime.now(TORONTO).date()
    season = today.year

    # Load confirmed lineups for today + tomorrow (covers early-posted games)
    lineup_rows = (
        supabase.table("mlb_lineups")
        .select("player_mlb_id,player_name,game_date")
        .gte("game_date", today.isoformat())
        .lte("game_date", (today + timedelta(days=1)).isoformat())
        .execute()
        .data
    )

    if not lineup_rows:
        print("No confirmed lineups found — skipping batter split sync.")
        updated_hands = _enrich_pitcher_hands(today)
        print(f"✅ Pitcher hands enriched: {updated_hands} (no lineups today)")
        return

    # Deduplicate: each player fetched once regardless of doubleheader/multi-game
    players = {}
    for r in lineup_rows:
        pid = r.get("player_mlb_id")
        if pid and pid not in players:
            players[pid] = r.get("player_name", "Unknown")

    saved = errors = skipped = 0
    for player_id, player_name in players.items():
        try:
            splits = _fetch_split_stats(player_id, season)
            time.sleep(0.1)
        except Exception as e:
            print(f"  {player_name} (id={player_id}): split fetch failed: {e}")
            errors += 1
            continue

        if not splits:
            skipped += 1
            continue

        for code, stat in splits.items():
            split_key = "vL" if code == "vl" else "vR"
            ops_idx, shrunk_idx, sample_wt = _shrunk_ops_index(stat, split_key)

            row = {
                "player_mlb_id": player_id,
                "player_name": player_name,
                "game_date": today.isoformat(),
                "season": season,
                "split": split_key,
                "at_bats": int(_safe(stat.get("atBats"), 0)),
                "hits": int(_safe(stat.get("hits"), 0)),
                "doubles": int(_safe(stat.get("doubles"), 0)),
                "triples": int(_safe(stat.get("triples"), 0)),
                "home_runs": int(_safe(stat.get("homeRuns"), 0)),
                "walks": int(_safe(stat.get("baseOnBalls"), 0)),
                "obp": round(_safe(stat.get("obp")), 4) or None,
                "slg": round(_safe(stat.get("slg")), 4) or None,
                "ops": round(_safe(stat.get("ops")), 4) or None,
                "ops_index": ops_idx,
                "shrunk_ops_index": shrunk_idx,
                "sample_weight": sample_wt,
                "synced_at": datetime.now(ZoneInfo("UTC")).isoformat(),
            }
            supabase.table("mlb_batter_strength").upsert(
                row, on_conflict="player_mlb_id,game_date,split"
            ).execute()
            saved += 1

    updated_hands = _enrich_pitcher_hands(today)

    print(
        f"\n✅ MLB batter stats synced: {saved} split rows | "
        f"{len(players)} unique players | {skipped} no-split-data | {errors} errors | "
        f"pitcher hands enriched: {updated_hands}"
    )


if __name__ == "__main__":
    main()
