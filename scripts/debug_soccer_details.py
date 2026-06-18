from src.ingestion.apisports_client import APISportsClient

client = APISportsClient()

fixture_id = 1374217  # replace with one actual fixture id if needed

print("STATISTICS")
print(client.get_soccer_fixture_statistics(fixture_id))

print("\nEVENTS")
print(client.get_soccer_fixture_events(fixture_id))

print("\nLINEUPS")
print(client.get_soccer_fixture_lineups(fixture_id))

print("\nPLAYERS")
print(client.get_soccer_fixture_players(fixture_id))
