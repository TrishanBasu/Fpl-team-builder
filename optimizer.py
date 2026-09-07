import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
import numpy as np


def build_best_team(df, budget=100):

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

    # Budget
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

    result = milp(
        c=objective,
        integrality=np.ones(n),
        bounds=Bounds(
            np.zeros(n),
            np.ones(n)
        ),
        constraints=LinearConstraint(
            np.array(constraints),
            np.array(lower_bounds),
            np.array(upper_bounds)
        )
    )

    if not result.success:
        return pd.DataFrame()

    return players[
        result.x > 0.5
    ].copy()


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

    for position, required in required_positions.items():

        count = (
            squad["position_name"] == position
        ).sum()

        if count != required:
            return False

    total_cost = pd.to_numeric(
        squad["now_cost"],
        errors="coerce"
    ).sum()

    if total_cost > budget:
        return False

    club_counts = (
        squad["club_name"]
        .value_counts()
    )

    if not club_counts.empty:
        if club_counts.max() > 3:
            return False

    return True


def find_transfer_suggestions(
    df,
    current_squad,
    budget=100
):

    current_squad = current_squad.copy()

    current_names = set(
        current_squad["player_name"]
    )

    current_total_score = (
        pd.to_numeric(
            current_squad["5GW Score"],
            errors="coerce"
        ).fillna(0).sum()
    )

    suggestions = []

    # Only consider players who could realistically
    # improve the squad.
    available_players = df[
        ~df["player_name"].isin(current_names)
    ].copy()

    available_players["5GW Score"] = pd.to_numeric(
        available_players["5GW Score"],
        errors="coerce"
    ).fillna(0)

    available_players["now_cost"] = pd.to_numeric(
        available_players["now_cost"],
        errors="coerce"
    ).fillna(0)

    current_squad["now_cost"] = pd.to_numeric(
        current_squad["now_cost"],
        errors="coerce"
    ).fillna(0)

    # Sort best players first
    available_players = available_players.sort_values(
        "5GW Score",
        ascending=False
    )

    # IMPORTANT:
    # Only test the best candidates at each position.
    # This makes Streamlit Cloud dramatically faster.
    candidates_per_position = 30

    for current_index, current_player in current_squad.iterrows():

        position = current_player["position_name"]

        current_name = current_player["player_name"]

        current_price = float(
            current_player["now_cost"]
        )

        current_score = float(
            current_player["5GW Score"]
        )

        # Players in same position
        alternatives = available_players[
            available_players["position_name"] == position
        ].copy()

        # Only keep the top 30 candidates
        alternatives = alternatives.head(
            candidates_per_position
        )

        # Don't even test players who score lower
        # than the player being sold.
        alternatives = alternatives[
            alternatives["5GW Score"] > current_score
        ]

        for _, new_player in alternatives.iterrows():

            # Quick budget check
            new_total_cost = (
                current_squad["now_cost"].sum()
                - current_price
                + float(new_player["now_cost"])
            )

            if new_total_cost > budget:
                continue

            # Quick club check
            new_club = new_player["club_name"]

            old_club = current_player["club_name"]

            if new_club != old_club:

                new_club_count = (
                    current_squad["club_name"]
                    .eq(new_club)
                    .sum()
                )

                if new_club_count >= 3:
                    continue

            # Create new squad
            new_squad = current_squad.copy()

            new_squad.loc[
                current_index
            ] = new_player

            if not is_valid_squad(
                new_squad,
                budget=budget
            ):
                continue

            new_total_score = (
                pd.to_numeric(
                    new_squad["5GW Score"],
                    errors="coerce"
                ).fillna(0).sum()
            )

            gain = (
                new_total_score
                - current_total_score
            )

            if gain <= 0:
                continue

            new_price = float(
                new_player["now_cost"]
            )

            price_change = (
                new_price
                - current_price
            )

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

    results = results.sort_values(
        "Gain",
        ascending=False
    )

    results = results.drop_duplicates(
        subset=["Sell", "Buy"]
    )

    return results.reset_index(
        drop=True
    )
