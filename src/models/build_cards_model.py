from supabase import create_client
from src.config.settings import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def main():
    games = (
        supabase.table("games")
        .select("id, home_team_name, away_team_name, raw_json")
        .eq("sport_key", "soccer")
        .in_("league_key", ["1", "479"])
        .limit(100)
        .execute()
        .data
    )

    saved = 0

    for game in games:
        raw = game.get("raw_json") or {}
        enriched = raw.get("enriched_details") or {}
        events = enriched.get("events", {}).get("response", [])

        yellow_cards = 0
        red_cards = 0

        for event in events:
            if event.get("type") == "Card":
                detail = event.get("detail", "")
                if "Yellow" in detail:
                    yellow_cards += 1
                if "Red" in detail:
                    red_cards += 1

        expected_cards = max(3.5, yellow_cards + red_cards * 2)

        over35 = 62 if expected_cards >= 4 else 48
        over45 = 56 if expected_cards >= 5 else 38

        if over35 >= 55:
            pick = "Over 3.5 Cards"
            conf = over35
        else:
            pick = "Pass"
            conf = over35

        row = {
            "game_id": game["id"],
            "home_team_name": game["home_team_name"],
            "away_team_name": game["away_team_name"],
            "expected_cards": expected_cards,
            "over_35_probability": over35,
            "over_45_probability": over45,
            "cards_pick": pick,
            "confidence": conf,
        }

        supabase.table("soccer_cards_predictions").insert(row).execute()
        saved += 1

    print(f"✅ Cards predictions created: {saved}")


if __name__ == "__main__":
    main()
    