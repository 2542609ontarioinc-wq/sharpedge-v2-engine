from src.ingestion.apisports_client import APISportsClient


def get_last_matches_for_team(team_api_id, season=2026, last=5):
    client = APISportsClient()

    return client._get(
        f"{client.football_base_url}/fixtures",
        params={
            "team": team_api_id,
            "season": season,
            "last": last,
        },
    )
    