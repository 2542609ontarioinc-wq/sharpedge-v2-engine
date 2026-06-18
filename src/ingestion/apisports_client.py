import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from src.config.settings import APISPORTS_KEY


class APISportsClient:
    def __init__(self):
        self.football_base_url = "https://v3.football.api-sports.io"
        self.baseball_base_url = "https://v1.baseball.api-sports.io"
        self.headers = {
            "x-apisports-key": APISPORTS_KEY
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get(self, url, params=None):
        response = requests.get(url, headers=self.headers, params=params, timeout=30)

        if response.status_code != 200:
            raise Exception(f"API-Sports error {response.status_code}: {response.text}")

        data = response.json()

        if "errors" in data and data["errors"]:
            raise Exception(f"API-Sports returned errors: {data['errors']}")

        return data

    # =====================
    # SOCCER
    # =====================

    def get_status(self):
        return self._get(f"{self.football_base_url}/status")

    def get_soccer_fixtures_by_date(self, date_str):
        return self._get(
            f"{self.football_base_url}/fixtures",
            params={"date": date_str}
        )

    def get_soccer_live_fixtures(self):
        return self._get(
            f"{self.football_base_url}/fixtures",
            params={"live": "all"}
        )

    def get_soccer_fixture_statistics(self, fixture_id):
        return self._get(
            f"{self.football_base_url}/fixtures/statistics",
            params={"fixture": fixture_id}
        )

    def get_soccer_fixture_events(self, fixture_id):
        return self._get(
            f"{self.football_base_url}/fixtures/events",
            params={"fixture": fixture_id}
        )

    def get_soccer_fixture_lineups(self, fixture_id):
        return self._get(
            f"{self.football_base_url}/fixtures/lineups",
            params={"fixture": fixture_id}
        )

    def get_soccer_fixture_players(self, fixture_id):
        return self._get(
            f"{self.football_base_url}/fixtures/players",
            params={"fixture": fixture_id}
        )

    def get_soccer_injuries_by_fixture(self, fixture_id):
        return self._get(
            f"{self.football_base_url}/injuries",
            params={"fixture": fixture_id}
        )

    def get_soccer_standings(self, league_id, season):
        return self._get(
            f"{self.football_base_url}/standings",
            params={"league": league_id, "season": season}
        )

    # =====================
    # MLB / BASEBALL
    # =====================

    def get_baseball_games_by_date(self, date_str):
        return self._get(
            f"{self.baseball_base_url}/games",
            params={"date": date_str}
        )

    def get_baseball_games_by_league_date(self, date_str, league_id=1, season=None):
        if season is None:
            season = int(date_str[:4])
        return self._get(
            f"{self.baseball_base_url}/games",
            params={"date": date_str, "league": league_id, "season": season}
        )

    def get_baseball_teams(self, league_id=1, season=None):
        params = {"league": league_id}
        if season:
            params["season"] = season

        return self._get(
            f"{self.baseball_base_url}/teams",
            params=params
        )

    def get_baseball_standings(self, league_id=1, season=None):
        params = {"league": league_id}
        if season:
            params["season"] = season

        return self._get(
            f"{self.baseball_base_url}/standings",
            params=params
        )
        