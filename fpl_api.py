import requests
import pandas as pd


BASE_URL = "https://fantasy.premierleague.com/api"


def get_fpl_data():
    """Get current player, team and gameweek data."""

    url = f"{BASE_URL}/bootstrap-static/"

    response = requests.get(
        url,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


def get_fixtures():
    """Get all current FPL fixtures."""

    url = f"{BASE_URL}/fixtures/"

    response = requests.get(
        url,
        timeout=20
    )

    response.raise_for_status()

    return response.json()


def get_next_5_gameweeks(fixtures):
    """Find the next 5 Gameweeks with unfinished fixtures."""

    upcoming = set()

    for fixture in fixtures:

        event = fixture.get("event")

        if event is None:
            continue

        if fixture.get("finished"):
            continue

        upcoming.add(event)

    return sorted(upcoming)[:5]


def calculate_fixture_difficulty(
    fixtures,
    team_id,
    next_5_gws
):
    """Calculate average fixture difficulty for the next 5 GWs."""

    difficulties = []

    for fixture in fixtures:

        if fixture.get("event") not in next_5_gws:
            continue

        if fixture.get("finished"):
            continue

        if fixture.get("team_h") == team_id:

            difficulty = fixture.get(
                "team_h_difficulty"
            )

            if difficulty is not None:
                difficulties.append(difficulty)

        elif fixture.get("team_a") == team_id:

            difficulty = fixture.get(
                "team_a_difficulty"
            )

            if difficulty is not None:
                difficulties.append(difficulty)

    if not difficulties:
        return None

    return round(
        sum(difficulties) / len(difficulties),
        2
    )


def prepare_player_dataframe(fpl_data):
    """
    Convert official FPL API player data
    into a pandas DataFrame.
    """

    players = pd.DataFrame(
        fpl_data["elements"]
    )

    teams = pd.DataFrame(
        fpl_data["teams"]
    )

    # FPL position IDs
    position_map = {
        1: "GKP",
        2: "DEF",
        3: "MID",
        4: "FWD"
    }

    players["position_name"] = (
        players["element_type"]
        .map(position_map)
    )

    # Team ID → Team Name
    team_map = dict(
        zip(
            teams["id"],
            teams["name"]
        )
    )

    players["club_name"] = (
        players["team"]
        .map(team_map)
    )

    # Player name
    players["player_name"] = (
        players["web_name"]
        .fillna(
            players["first_name"]
            + " "
            + players["second_name"]
        )
    )

    # Official FPL API price:
    # 150 = £15.0m
    players["now_cost"] = (
        pd.to_numeric(
            players["now_cost"],
            errors="coerce"
        )
        / 10
    )

    # Make sure numerical columns are numeric
    numeric_columns = [
        "form",
        "points_per_game",
        "total_points",
        "expected_goals",
        "expected_assists",
        "minutes",
        "selected_by_percent"
    ]

    for column in numeric_columns:

        if column in players.columns:

            players[column] = pd.to_numeric(
                players[column],
                errors="coerce"
            )

    return players
