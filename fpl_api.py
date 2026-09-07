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

    gameweeks = []

    for fixture in fixtures:

        if (
            not fixture["finished"]
            and fixture["event"] is not None
        ):

            if fixture["event"] not in gameweeks:
                gameweeks.append(fixture["event"])

    gameweeks.sort()

    return gameweeks[:5]


def calculate_fixture_difficulty(
    fixtures,
    team_id,
    next_5_gws
):

    difficulties = []

    for fixture in fixtures:

        if (
            fixture["event"] in next_5_gws
            and not fixture["finished"]
        ):

            if fixture["team_h"] == team_id:

                difficulties.append(
                    fixture["team_h_difficulty"]
                )

            elif fixture["team_a"] == team_id:

                difficulties.append(
                    fixture["team_a_difficulty"]
                )

    if not difficulties:
        return None

    return round(
        sum(difficulties) / len(difficulties),
        2
    )
