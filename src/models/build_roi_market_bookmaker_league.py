from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    rows = (
        supabase.table("final_soccer_predictions")
        .select("*")
        .not_.is_("bookmaker", "null")
        .execute()
        .data
    )

    grouped = {}

    for row in rows:
        game = (
            supabase.table("games")
            .select("league_key")
            .eq("id", row["game_id"])
            .limit(1)
            .execute()
            .data
        )

        league_key = game[0]["league_key"] if game else None

        key = (
            row["market"],
            row["bookmaker"],
            league_key,
        )

        grouped.setdefault(
            key,
            {
                "total": 0,
                "wins": 0,
                "losses": 0,
            },
        )

        grouped[key]["total"] += 1

        # Until fully graded, treat as pending.
        # Professional ROI should use actual grades only.
        # For now we only store exposure count.
        grouped[key]["losses"] += 0

    saved = 0

    for key, stats in grouped.items():
        market, bookmaker, league_key = key

        total = stats["total"]
        wins = stats["wins"]
        losses = stats["losses"]

        total_staked = total * 1
        profit = round((wins * 0.91) - losses, 2)
        roi = round((profit / total_staked) * 100, 2) if total_staked else 0

        supabase.table("soccer_roi_market_bookmaker_league").insert(
            {
                "market": market,
                "bookmaker": bookmaker,
                "league_key": league_key,
                "total_bets": total,
                "wins": wins,
                "losses": losses,
                "total_staked": total_staked,
                "profit_units": profit,
                "roi_percentage": roi,
            }
        ).execute()

        saved += 1

    print(f"✅ ROI by market/bookmaker/league rows created: {saved}")


if __name__ == "__main__":
    main()
    