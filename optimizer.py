import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
import numpy as np


# ============================================================
# BUILD BEST £100m TEAM
# ============================================================

def build_best_team(df, budget=100):

    players = df.copy()

    # Your CSV stores prices directly in £m
    players["price"] = pd.to_numeric(
        players["now_cost"],
        errors="coerce"
    ).fillna(0)

    players["5GW Score"] = pd.to_numeric(
        players["5GW Score"],
        errors="coerce"
    ).fillna(0)

    # Actual position codes in your CSV
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

    # Maximize 5GW Score
    objective = -players["5GW Score"].values

    constraints = []
    lower_bounds = []
    upper_bounds = []

    # --------------------------------------------------------
    # POSITION REQUIREMENTS
    # --------------------------------------------------------

    for position, required in position_requirements.items():

        row = (
            players["position_name"] == position
        ).astype(int).values

        constraints.append(row)
        lower_bounds.append(required)
        upper_bounds.append(required)

    # --------------------------------------------------------
    # £100m BUDGET
    # --------------------------------------------------------

    constraints.append(
        players["price"].values
    )

    lower_bounds.append(0)
    upper_bounds.append(budget)

    # --------------------------------------------------------
    # MAX 3 PLAYERS FROM ONE CLUB
    # --------------------------------------------------------

    for club in players["club_name"].dropna().unique():

        row = (
            players["club_name"] == club
        ).astype(int).values

        constraints.append(row)
        lower_bounds.append(0)
        upper_bounds.append(3)

    # --------------------------------------------------------
    # SOLVER
    # --------------------------------------------------------

    constraint_matrix = np.array(
        constraints
    )

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


# ============================================================
# CHECK VALID SQUAD
# ============================================================

def is_valid_squad(
    squad,
    budget=100
):

    if len(squad) != 15:
        return False

    required_positions = {
        "GKP": 2,
        "DEF": 5,
        "MID": 5,
        "FWD": 3
    }

    # Position validation
    for position, required in (
        required_positions.items()
    ):

        count = (
            squad["position_name"] == position
        ).sum()

        if count != required:
            return False

    # Budget validation
    total_cost = pd.to_numeric(
        squad["now_cost"],
        errors="coerce"
    ).sum()

    if total_cost > budget:
        return False

    # Club limit
    club_counts = (
        squad["club_name"]
        .value_counts()
    )

    if not club_counts.empty:

        if club_counts.max() > 3:
            return False

    return True


# ============================================================
# FIND LEGAL SINGLE TRANSFERS
# ============================================================

def find_transfer_suggestions(
    df,
    current_squad,
    budget=100
):

    suggestions = []

    current_names = set(
        current_squad["player_name"]
    )

    current_total_score = (
        current_squad["5GW Score"].sum()
    )

    # Players outside current squad
    available_players = df[
        ~df["player_name"].isin(
            current_names
        )
    ].copy()

    # --------------------------------------------------------
    # TRY EVERY POSSIBLE PLAYER SWAP
    # --------------------------------------------------------

    for current_index, current_player in (
        current_squad.iterrows()
    ):

        position = (
            current_player["position_name"]
        )

        current_name = (
            current_player["player_name"]
        )

        current_price = float(
            current_player["now_cost"]
        )

        current_score = float(
            current_player["5GW Score"]
        )

        # Same-position replacements only
        alternatives = available_players[
            available_players["position_name"]
            == position
        ].copy()

        for _, new_player in (
            alternatives.iterrows()
        ):

            # Create hypothetical squad
            new_squad = current_squad.copy()

            new_squad.loc[
                current_index
            ] = new_player

            # Make sure new squad is legal
            if not is_valid_squad(
                new_squad,
                budget=budget
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

            # Only show improvements
            if gain <= 0:
                continue

            new_price = float(
                new_player["now_cost"]
            )

            # Direct £m difference
            price_change = (
                new_price
                -
                current_price
            )

            suggestions.append({

                "Sell": current_name,

                "Buy": new_player[
                    "player_name"
                ],

                "Position": position,

                "Current Score": round(
                    current_score,
                    2
                ),

                "New Score": round(
                    float(
                        new_player[
                            "5GW Score"
                        ]
                    ),
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

                "New Club": new_player[
                    "club_name"
                ]

            })

    if not suggestions:
        return pd.DataFrame()

    results = pd.DataFrame(
        suggestions
    )

    # Best projected improvement first
    results = results.sort_values(
        "Gain",
        ascending=False
    )

    # Remove duplicate transfers
    results = results.drop_duplicates(
        subset=[
            "Sell",
            "Buy"
        ]
    )

    return results.reset_index(
        drop=True
    )
