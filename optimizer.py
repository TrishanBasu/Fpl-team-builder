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

    position_requirements = {
        "Goalkeeper": 2,
        "Defender": 5,
        "Midfielder": 5,
        "Forward": 3
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

    # -----------------------------
    # POSITION REQUIREMENTS
    # -----------------------------

    for position, required in position_requirements.items():

        row = (
            players["position_name"] == position
        ).astype(int).values

        constraints.append(row)
        lower_bounds.append(required)
        upper_bounds.append(required)

    # -----------------------------
    # TOTAL BUDGET
    # -----------------------------

    constraints.append(
        players["price"].values
    )

    lower_bounds.append(0)
    upper_bounds.append(budget)

    # -----------------------------
    # MAX 3 PLAYERS PER CLUB
    # -----------------------------

    for club in players["club_name"].dropna().unique():

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
# CHECK WHETHER A SQUAD IS LEGAL
# ============================================================

def is_valid_squad(squad, budget=1000):

    if len(squad) != 15:
        return False

    required_positions = {
        "Goalkeeper": 2,
        "Defender": 5,
        "Midfielder": 5,
        "Forward": 3
    }

    # Position check
    for position, required in required_positions.items():

        count = (
            squad["position_name"] == position
        ).sum()

        if count != required:
            return False

    # Budget check
    total_cost = squad["now_cost"].sum()

    if total_cost > budget:
        return False

    # Club limit
    club_counts = squad["club_name"].value_counts()

    if club_counts.max() > 3:
        return False

    return True


# ============================================================
# FIND VALID SINGLE TRANSFERS
# ============================================================

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

    # Players who can potentially be bought
    available_players = df[
        ~df["player_name"].isin(current_names)
    ].copy()

    # Try replacing every player
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

        # Only same-position replacements
        alternatives = available_players[
            available_players["position_name"] == position
        ].copy()

        for _, new_player in alternatives.iterrows():

            new_price = float(
                new_player["now_cost"]
            )

            # Create hypothetical squad
            new_squad = current_squad.copy()

            new_squad.loc[
                current_index
            ] = new_player

            # Check legal squad
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

            # Only recommend improvements
            if gain <= 0:
                continue

            price_change = (
                new_price - current_price
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

    results = pd.DataFrame(
        suggestions
    )

    # Best improvements first
    results = results.sort_values(
        "Gain",
        ascending=False
    )

    # Remove duplicate recommendations
    results = results.drop_duplicates(
        subset=["Sell", "Buy"]
    )

    return results.reset_index(
        drop=True
    )
