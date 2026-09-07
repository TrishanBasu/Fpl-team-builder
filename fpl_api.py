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
