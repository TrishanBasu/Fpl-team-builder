import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
import numpy as np


def build_best_team(df, budget=1000):

    players = df.copy()

    players["price"] = pd.to_numeric(
        players["now_cost"],
        errors="coerce"
    ).fillna(0)

    players["5GW Score"] = pd.to_numeric(
        players["5GW Score"],
        errors="coerce"
    ).fillna(0)

    # Actual position codes in the dataset
    position_requirements = {
        "GKP": 2,
        "DEF": 5,
        "MID": 5,
        "FWD": 3
    }

    players = players[
        players["position_name"].isin(
            position_requirements.keys()
        )
    ].reset_index(drop=True)

    n = len(players)

    if n == 0:
        return pd.DataFrame()

    objective = -players["5GW Score"].values

    constraints = []
    lower_bounds = []
    upper_bounds = []

    # Position requirements
    for position, required in position_requirements.items():

        row = (
            players["position_name"] == position
        ).astype(int).values

        constraints.append(row)
        lower_bounds.append(required)
        upper_bounds.append(required)

    # £100m budget
    constraints.append(
        players["price"].values
    )

    lower_bounds.append(0)
    upper_bounds.append(budget)

    # Maximum 3 players from one club
    for club in players["club_name"].dropna().unique():

        row = (
            players["club_name"] == club
        ).astype(int).values

        constraints.append(row)
        lower_bounds.append(0)
        upper_bounds.append(3)

    constraint_matrix = np.array(constraints)

    linear_constraint = LinearConstraint(
        constraint_matrix,
        np.array(lower_bounds),
        np.array(upper_bounds)
    )

    result = milp(
        c=objective,
        integrality=np.ones(n),
        bounds=Bounds(
            np.zeros(n),
            np.ones(n)
        ),
        constraints=linear_constraint
    )

    if not result.success:
        return pd.DataFrame()

    selected = players[
        result.x > 0.5
    ].copy()

    return selected


def is_valid_squad(squad, budget=1000):

    if len(squad) != 15:
        return False

    required_positions = {
        "GKP": 2,
        "DEF": 5,
        "MID": 5,
        "FWD": 3
    }

    for position, required in required_positions.items():

        count = (
            squad["position_name"] == position
        ).sum()

        if count != required:
            return False

    total_cost = squad["now_cost"].sum()

    if total_cost > budget:
        return False

    club_counts = squad["club_name"].value_counts()

    if not club_counts.empty and club_counts.max() > 3:
        return False

    return True


def find_transfer_suggestions(
    df,
    current_squad,
    budget=1000
):

    suggestions = []

    current_names = set(
        current_squad["player_name"]
    )

    current_total_score = (
        current_squad["5GW Score"].sum()
    )

    available_players = df[
        ~df["player_name"].isin(current_names)
    ].copy()

    for current_index, current_player in (
        current_squad.iterrows()
    ):

        position = current_player["position_name"]

        current_name = current_player["player_name"]

        current_price = float(
            current_player["now_cost"]
        )

        current_score = float(
            current_player["5GW Score"]
        )

        alternatives = available_players[
            available_players["position_name"] == position
        ].copy()

        for _, new_player in alternatives.iterrows():

            new_squad = current_squad.copy()

            new_squad.loc[
                current_index
            ] = new_player

            if not is_valid_squad(
                new_squad,
                budget
            ):
                continue

            new_total_score = (
                new_squad["5GW Score"].sum()
            )

            gain = (
                new_total_score
                -
                current_total_score
            )

            if gain <= 0:
                continue

            price_change = (
                float(new_player["now_cost"])
                -
                current_price
            ) / 10

            suggestions.append({

                "Sell": current_name,

                "Buy": new_player["player_name"],

                "Position": position,

                "Current Score": round(
                    current_score,
                    2
                ),

                "New Score": round(
                    float(new_player["5GW Score"]),
                    2
                ),

                "Gain": round(
                    gain,
                    2
                ),

                "Price Change (£m)": round(
                    price_change,
                    1
                ),

                "New Club": new_player["club_name"]

            })

    if not suggestions:
        return pd.DataFrame()

    results = pd.DataFrame(suggestions)

    results = results.sort_values(
        "Gain",
        ascending=False
    )

    results = results.drop_duplicates(
        subset=["Sell", "Buy"]
    )

    return results.reset_index(drop=True)
