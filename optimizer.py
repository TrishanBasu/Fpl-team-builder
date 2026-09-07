import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
import numpy as np


def build_best_team(df, budget=1000):

    players = df.copy()

    # FPL prices are stored as 10 = £1.0m
    players["price"] = pd.to_numeric(
        players["now_cost"],
        errors="coerce"
    ).fillna(0)

    # Make sure score is numeric
    players["5GW Score"] = pd.to_numeric(
        players["5GW Score"],
        errors="coerce"
    ).fillna(0)

    # Position mapping
    position_requirements = {
        "Goalkeeper": 2,
        "Defender": 5,
        "Midfielder": 5,
        "Forward": 3
    }

    # Remove players without valid position
    players = players[
        players["position_name"].isin(
            position_requirements.keys()
        )
    ].reset_index(drop=True)

    n = len(players)

    if n == 0:
        return pd.DataFrame()

    # Objective:
    # maximize 5GW score
    objective = -players["5GW Score"].values

    # --------------------------------------------------
    # POSITION CONSTRAINTS
    # --------------------------------------------------

    constraints = []
    lower_bounds = []
    upper_bounds = []

    for position, required in position_requirements.items():

        row = (
            players["position_name"] == position
        ).astype(int).values

        constraints.append(row)

        lower_bounds.append(required)
        upper_bounds.append(required)

    # --------------------------------------------------
    # BUDGET CONSTRAINT
    # --------------------------------------------------

    constraints.append(
        players["price"].values
    )

    lower_bounds.append(0)
    upper_bounds.append(budget)

    # --------------------------------------------------
    # CLUB LIMIT
    # --------------------------------------------------

    for club in players["club_name"].unique():

        row = (
            players["club_name"] == club
        ).astype(int).values

        constraints.append(row)

        lower_bounds.append(0)
        upper_bounds.append(3)

    constraint_matrix = np.array(
        constraints
    )

    linear_constraint = LinearConstraint(
        constraint_matrix,
        np.array(lower_bounds),
        np.array(upper_bounds)
    )

    # --------------------------------------------------
    # SOLVE
    # --------------------------------------------------

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
