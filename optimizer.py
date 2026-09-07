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
    FPL squad within the budget.
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

    # ------------------------------------------------
    # Position constraints
    # ------------------------------------------------

    for position, required in (
        POSITION_REQUIREMENTS.items()
    ):

        row = (
            players["position_name"]
            == position
        ).astype(int).values

        constraints.append(row)

        lower_bounds.append(
            required
        )

        upper_bounds.append(
            required
        )

    # ------------------------------------------------
    # £100m budget
    # ------------------------------------------------

    constraints.append(
        players["price"].values
    )

    lower_bounds.append(0)

    upper_bounds.append(
        budget
    )

    # ------------------------------------------------
    # Maximum 3 players from one club
    # ------------------------------------------------

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

    # ------------------------------------------------
    # Solve optimization problem
    # ------------------------------------------------

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


def is_valid_squad(
    squad,
    budget=100
):
    """
    Check whether a 15-player squad follows
    the basic FPL squad rules.
    """

    if len(squad) != 15:
        return False

    # Position rules
    for position, required in (
        POSITION_REQUIREMENTS.items()
    ):

        count = (
            squad["position_name"]
            == position
        ).sum()

        if count != required:
            return False

    # Budget
    total_cost = pd.to_numeric(
        squad["now_cost"],
        errors="coerce"
    ).fillna(0).sum()

    if total_cost > budget:
        return False

    # Maximum 3 from one club
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
    Find legal single-player transfers that
    improve the projected 5GW score.

    Uses a limited number of high-scoring candidates
    to keep Streamlit Cloud fast.
    """

    current_squad = (
        current_squad.copy()
    )

    current_names = set(
        current_squad[
            "player_name"
        ]
    )

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

    # Only test top candidates at each position
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

        # Only players who are projected
        # to score better
        alternatives = alternatives[
            alternatives[
                "5GW Score"
            ] > current_score
        ]

        for _, new_player in (
            alternatives.iterrows()
        ):

            new_price = float(
                new_player[
                    "now_cost"
                ]
            )

            # Quick budget check
            new_total_cost = (
                current_squad[
                    "now_cost"
                ].sum()
                - current_price
                + new_price
            )

            if new_total_cost > budget:
                continue

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

            # Quick club check
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

            # Create replacement squad
            new_squad = (
                current_squad.copy()
            )

            new_squad.loc[
                current_index
            ] = new_player

            if not is_valid_squad(
                new_squad,
                budget=budget
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
