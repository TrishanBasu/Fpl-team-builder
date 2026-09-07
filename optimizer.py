import pandas as pd
import numpy as np

from scipy.optimize import (
    milp,
    LinearConstraint,
    Bounds
)


POSITION_REQUIREMENTS = {
    "GKP": 2,
    "DEF": 5,
    "MID": 5,
    "FWD": 3
}


def build_best_team(
    df,
    budget=100
):
    """
    Build the highest-scoring legal 15-player
    FPL squad within the £100m budget.
    """

    players = df.copy()

    players["price"] = pd.to_numeric(
        players["now_cost"],
        errors="coerce"
    ).fillna(0)

    players["5GW Score"] = pd.to_numeric(
        players["5GW Score"],
        errors="coerce"
    ).fillna(0)

    players = players[
        players["position_name"].isin(
            POSITION_REQUIREMENTS
        )
    ].reset_index(drop=True)

    if players.empty:
        return pd.DataFrame()

    n = len(players)

    objective = -players[
        "5GW Score"
    ].values

    constraints = []
    lower_bounds = []
    upper_bounds = []

    # Position requirements
    for position, required in (
        POSITION_REQUIREMENTS.items()
    ):

        row = (
            players["position_name"]
            == position
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
    for club in (
        players["club_name"]
        .dropna()
        .unique()
    ):

        row = (
            players["club_name"]
            == club
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


def is_valid_squad_structure(
    squad
):
    """
    Validate the actual FPL squad structure.

    IMPORTANT:
    This does NOT check the £100m current value.

    Player prices can rise after a user bought them,
    so current market value is not the same as the
    original squad budget.
    """

    if len(squad) != 15:
        return False

    for position, required in (
        POSITION_REQUIREMENTS.items()
    ):

        count = (
            squad["position_name"]
            == position
        ).sum()

        if count != required:
            return False

    club_counts = (
        squad["club_name"]
        .value_counts()
    )

    if (
        not club_counts.empty
        and club_counts.max() > 3
    ):
        return False

    return True


def find_transfer_suggestions(
    df,
    current_squad,
    budget=100
):
    """
    Find legal single-player transfer suggestions.

    The current squad's present market value is NOT
    used to reject the squad.

    Transfers are compared using current player prices.
    Exact FPL affordability can depend on the user's
    individual selling prices and bank balance, which
    are not available from the public player API.
    """

    current_squad = current_squad.copy()

    # Make sure each player is unique
    if "id" in current_squad.columns:

        current_squad = (
            current_squad
            .drop_duplicates(
                subset=["id"]
            )
        )

    # A valid FPL squad must contain exactly 15 players
    if len(current_squad) != 15:
        return pd.DataFrame()

    current_squad["now_cost"] = pd.to_numeric(
        current_squad["now_cost"],
        errors="coerce"
    ).fillna(0)

    current_squad["5GW Score"] = pd.to_numeric(
        current_squad["5GW Score"],
        errors="coerce"
    ).fillna(0)

    current_total_score = (
        current_squad[
            "5GW Score"
        ].sum()
    )

    # Use unique FPL player IDs
    if "id" in current_squad.columns:

        current_ids = set(
            current_squad["id"]
        )

        available_players = df[
            ~df["id"].isin(current_ids)
        ].copy()

    else:

        # Fallback
        current_names = set(
            current_squad[
                "player_name"
            ]
        )

        available_players = df[
            ~df[
                "player_name"
            ].isin(current_names)
        ].copy()

    available_players[
        "now_cost"
    ] = pd.to_numeric(
        available_players["now_cost"],
        errors="coerce"
    ).fillna(0)

    available_players[
        "5GW Score"
    ] = pd.to_numeric(
        available_players["5GW Score"],
        errors="coerce"
    ).fillna(0)

    available_players = (
        available_players
        .sort_values(
            "5GW Score",
            ascending=False
        )
    )

    suggestions = []

    candidates_per_position = 30

    for current_index, current_player in (
        current_squad.iterrows()
    ):

        position = (
            current_player[
                "position_name"
            ]
        )

        current_name = (
            current_player[
                "player_name"
            ]
        )

        current_price = float(
            current_player[
                "now_cost"
            ]
        )

        current_score = float(
            current_player[
                "5GW Score"
            ]
        )

        alternatives = (
            available_players[
                available_players[
                    "position_name"
                ] == position
            ]
            .head(
                candidates_per_position
            )
        )

        # Only consider players with a better
        # projected 5GW score
        alternatives = alternatives[
            alternatives[
                "5GW Score"
            ] > current_score
        ]

        for _, new_player in (
            alternatives.iterrows()
        ):

            new_club = (
                new_player[
                    "club_name"
                ]
            )

            old_club = (
                current_player[
                    "club_name"
                ]
            )

            # Maximum 3 players from one club
            if new_club != old_club:

                new_club_count = (
                    current_squad[
                        "club_name"
                    ]
                    .eq(new_club)
                    .sum()
                )

                if new_club_count >= 3:
                    continue

            # Create the new squad
            new_squad = (
                current_squad.copy()
            )

            new_squad.loc[
                current_index
            ] = new_player

            # Check squad structure only
            if not is_valid_squad_structure(
                new_squad
            ):
                continue

            new_total_score = (
                new_squad[
                    "5GW Score"
                ].sum()
            )

            gain = (
                new_total_score
                - current_total_score
            )

            if gain <= 0:
                continue

            new_price = float(
                new_player[
                    "now_cost"
                ]
            )

            price_change = (
                new_price
                - current_price
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

                "New Club": new_club
            })

    if not suggestions:
        return pd.DataFrame()

    results = pd.DataFrame(
        suggestions
    )

    results = (
        results
        .sort_values(
            "Gain",
            ascending=False
        )
        .drop_duplicates(
            subset=[
                "Sell",
                "Buy"
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return results
