import requests


def get_fpl_data():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    
    response = requests.get(url)
    response.raise_for_status()
    
    return response.json()


def get_fixtures():
    url = "https://fantasy.premierleague.com/api/fixtures/"
    
    response = requests.get(url)
    response.raise_for_status()
    
    return response.json()


def get_next_5_gameweeks(fixtures):
    current_gameweeks = []

    for fixture in fixtures:
        if not fixture["finished"] and fixture["event"] is not None:
            if fixture["event"] not in current_gameweeks:
                current_gameweeks.append(fixture["event"])

    current_gameweeks.sort()

    return current_gameweeks[:5]
