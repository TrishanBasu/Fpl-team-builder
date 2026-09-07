import streamlit as st
import pandas as pd

from fpl_api import (
    get_fpl_data,
    get_fixtures,
    get_next_5_gameweeks,
    calculate_fixture_difficulty,
    prepare_player_dataframe
)

from optimizer import (
    build_best_team,
    find_transfer_suggestions
)


# ==================================================
# PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="FPL 5-Gameweek Optimizer",
    page_icon="⚽",
    layout="wide"
)


# ==================================================
# TITLE
# ==================================================

st.title(
    "⚽ FPL 5-Gameweek Optimizer"
)

st.write(
    "Build the best £100m FPL team or find "
    "budget-aware transfer suggestions using "
    "the next 5 Gameweeks."
)

st.caption(
    "Live player and fixture data are retrieved "
    "from the official Fantasy Premier League API."
)


# ==================================================
# LOAD LIVE FPL DATA
# ==================================================

try:

    with st.spinner(
        "Loading live FPL data..."
    ):

        fpl_data = get_fpl_data()

        fixtures = get_fixtures()

except Exception as e:

    st.error(
        "❌ Could not connect to the official FPL API."
    )

    st.error(
        str(e)
    )

    st.stop()


# ==================================================
# PREPARE PLAYER DATA
# ==================================================

try:

    df = prepare_player_dataframe(
        fpl_data
    )

except Exception as e:

    st.error(
        "❌ Could not prepare FPL player data."
    )

    st.error(
        str(e)
    )

    st.stop()


# ==================================================
# FIND NEXT 5 GAMEWEEKS
# ==================================================

next_5_gws = (
    get_next_5_gameweeks(
        fixtures
    )
)


st.subheader(
    "📅 Next 5 Gameweeks"
)


if next_5_gws:

    st.info(
        " → ".join(
            [
                f"GW {gw}"
                for gw in next_5_gws
            ]
        )
    )

else:

    st.warning(
        "No upcoming Gameweeks found."
    )


# ==================================================
# CALCULATE FIXTURE DIFFICULTY
# ==================================================

fixture_scores = []


for _, player in df.iterrows():

    team_id = player["team"]

    difficulty = (
        calculate_fixture_difficulty(
            fixtures,
            team_id,
            next_5_gws
        )
    )

    fixture_scores.append(
        difficulty
    )


df[
    "5GW Avg Difficulty"
] = fixture_scores


# ==================================================
# NUMERIC COLUMNS
# ==================================================

numeric_columns = [
    "form",
    "points_per_game",
    "total_points",
    "expected_goals",
    "expected_assists",
    "now_cost"
]


for column in numeric_columns:

    if column not in df.columns:

        df[column] = 0

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ==================================================
# PERFORMANCE SCORE
# ==================================================

df[
    "Performance Score"
] = (

    df[
        "form"
    ].fillna(0)
    * 0.35

    +

    df[
        "points_per_game"
    ].fillna(0)
    * 0.30

    +

    (
        df[
            "total_points"
        ].fillna(0)
        / 10
    )
    * 0.20

    +

    df[
        "expected_goals"
    ].fillna(0)
    * 0.075

    +

    df[
        "expected_assists"
    ].fillna(0)
    * 0.075
)


# ==================================================
# FIXTURE FACTOR
# ==================================================

df[
    "Fixture Factor"
] = (

    6
    -
    df[
        "5GW Avg Difficulty"
    ].fillna(3)
)


# ==================================================
# 5 GAMEWEEK SCORE
# ==================================================

df[
    "5GW Score"
] = (

    df[
        "Performance Score"
    ]

    *

    df[
        "Fixture Factor"
    ]
)


# ==================================================
# DATA LOADED MESSAGE
# ==================================================

st.success(
    "🟢 Live FPL data loaded successfully"
)

st.caption(
    f"Players loaded: {len(df)}"
)


st.divider()


# ==================================================
# MAIN OPTIONS
# ==================================================

st.header(
    "What do you want to do?"
)


option = st.radio(
    "Choose an option",

    [
        "🏆 Build Full Team",
        "🔄 Transfer Suggestions"
    ],

    horizontal=True
)


# ==================================================
# BUILD FULL TEAM
# ==================================================

if option == "🏆 Build Full Team":

    st.subheader(
        "🏆 Best £100m Team"
    )

    st.write(
        "The optimizer selects the best 15-player "
        "squad using the next 5 Gameweeks while "
        "respecting the £100m budget and "
        "maximum 3 players per club."
    )


    if st.button(
        "🚀 Build My Team",
        type="primary"
    ):

        with st.spinner(
            "Building the best £100m squad..."
        ):

            best_team = build_best_team(
                df,
                budget=100
            )


        if best_team.empty:

            st.error(
                "❌ Could not find a valid £100m squad."
            )


        else:

            # --------------------------------------
            # PRICE
            # --------------------------------------

            best_team[
                "Price (£m)"
            ] = best_team[
                "price"
            ]


            total_cost = (
                best_team[
                    "price"
                ].sum()
            )


            st.success(
                f"✅ Team found! "
                f"Total cost: £{total_cost:.1f}m"
            )


            # --------------------------------------
            # POSITION ORDER
            # --------------------------------------

            position_order = {
                "GKP": 1,
                "DEF": 2,
                "MID": 3,
                "FWD": 4
            }


            best_team[
                "position_order"
            ] = (
                best_team[
                    "position_name"
                ]
                .map(
                    position_order
                )
            )


            best_team = (
                best_team
                .sort_values(
                    "position_order"
                )
            )


            # --------------------------------------
            # POSITION NAMES
            # --------------------------------------

            position_names = {
                "GKP": "Goalkeeper",
                "DEF": "Defender",
                "MID": "Midfielder",
                "FWD": "Forward"
            }


            best_team[
                "Position"
            ] = (
                best_team[
                    "position_name"
                ]
                .map(
                    position_names
                )
            )


            # --------------------------------------
            # DISPLAY TEAM
            # --------------------------------------

            display_columns = [
                "player_name",
                "club_name",
                "Position",
                "Price (£m)",
                "5GW Score",
                "5GW Avg Difficulty"
            ]


            st.dataframe(

                best_team[
                    display_columns
                ],

                use_container_width=True,

                hide_index=True
            )


            # --------------------------------------
            # SQUAD SUMMARY
            # --------------------------------------

            st.subheader(
                "📊 Squad Summary"
            )


            col1, col2, col3 = (
                st.columns(3)
            )


            with col1:

                st.metric(
                    "Squad Cost",
                    f"£{total_cost:.1f}m"
                )


            with col2:

                st.metric(
                    "Money Remaining",
                    f"£{100 - total_cost:.1f}m"
                )


            with col3:

                st.metric(
                    "Projected 5GW Score",
                    f"{best_team['5GW Score'].sum():.1f}"
                )


# ==================================================
# TRANSFER SUGGESTIONS
# ==================================================

else:

    st.subheader(
        "🔄 Transfer Suggestions"
    )


    st.write(
        "Select your current 15-man squad and "
        "enter your available bank balance. "
        "The optimizer will only recommend "
        "transfers you can afford."
    )


    # ==================================================
    # BANK BALANCE
    # ==================================================

    bank = st.number_input(

        "💰 Money in Bank (£m)",

        min_value=0.0,

        max_value=100.0,

        value=0.0,

        step=0.1,

        help=(
            "Enter the money currently available "
            "in your FPL bank."
        )
    )


    st.caption(
        f"Only transfers requiring £{bank:.1f}m "
        f"or less from your bank will be shown."
    )


    st.divider()


    # ==================================================
    # UNIQUE PLAYER OPTIONS
    # ==================================================

    df = df.copy()


    df[
        "player_option"
    ] = (

        df[
            "player_name"
        ].astype(str)

        + " — "

        + df[
            "club_name"
        ].astype(str)

        + " — "

        + df[
            "position_name"
        ].astype(str)

        + " — ID "

        + df[
            "id"
        ].astype(str)
    )


    player_options = (

        df[
            [
                "id",
                "player_option"
            ]
        ]

        .drop_duplicates(
            subset=[
                "id"
            ]
        )

        .sort_values(
            "player_option"
        )
    )


    # ==================================================
    # SELECT CURRENT SQUAD
    # ==================================================

    selected_options = st.multiselect(

        "Select your current squad (15 players)",

        player_options[
            "player_option"
        ].tolist(),

        max_selections=15
    )


    # Convert selected player options
    # into unique FPL player IDs

    selected_ids = (

        player_options[
            player_options[
                "player_option"
            ].isin(
                selected_options
            )
        ]

        [
            "id"
        ]

        .tolist()
    )


    # ==================================================
    # WAITING FOR 15 PLAYERS
    # ==================================================

    if len(selected_ids) < 15:

        st.info(

            f"Select "
            f"{15 - len(selected_ids)} "
            f"more player(s)."
        )


    else:

        st.success(
            "✅ 15 players selected!"
        )


        # ==================================================
        # CREATE CURRENT SQUAD
        # ==================================================

        current_squad = df[
            df[
                "id"
            ].isin(
                selected_ids
            )
        ].copy()


        # Extra duplicate protection

        current_squad = (

            current_squad

            .drop_duplicates(
                subset=[
                    "id"
                ]
            )
        )


        # ==================================================
        # CURRENT SQUAD DISPLAY
        # ==================================================

        st.subheader(
            "👥 Your Current Squad"
        )


        current_squad[
            "Price (£m)"
        ] = current_squad[
            "now_cost"
        ]


        position_names = {

            "GKP": "Goalkeeper",

            "DEF": "Defender",

            "MID": "Midfielder",

            "FWD": "Forward"
        }


        current_squad[
            "Position"
        ] = (

            current_squad[
                "position_name"
            ]

            .map(
                position_names
            )
        )


        current_display = [

            "player_name",

            "club_name",

            "Position",

            "Price (£m)",

            "5GW Score",

            "5GW Avg Difficulty"
        ]


        st.dataframe(

            current_squad[
                current_display
            ],

            use_container_width=True,

            hide_index=True
        )


        # ==================================================
        # SQUAD VALIDATION
        # ==================================================

        position_counts = (

            current_squad[
                "position_name"
            ]

            .value_counts()
        )


        total_current_value = (

            current_squad[
                "now_cost"
            ]

            .sum()
        )


        club_counts = (

            current_squad[
                "club_name"
            ]

            .value_counts()
        )


        invalid_reasons = []


        required_positions = {

            "GKP": 2,

            "DEF": 5,

            "MID": 5,

            "FWD": 3
        }


        position_display_names = {

            "GKP": "Goalkeepers",

            "DEF": "Defenders",

            "MID": "Midfielders",

            "FWD": "Forwards"
        }


        # ==================================================
        # POSITION VALIDATION
        # ==================================================

        for position, required in (
            required_positions.items()
        ):

            actual = position_counts.get(
                position,
                0
            )


            if actual != required:

                invalid_reasons.append(

                    f"{position_display_names[position]}: "
                    f"{actual}/{required}"
                )


        # ==================================================
        # CLUB VALIDATION
        # ==================================================

        if not club_counts.empty:

            if club_counts.max() > 3:

                invalid_clubs = (

                    club_counts[
                        club_counts > 3
                    ]
                )


                for club, count in (
                    invalid_clubs.items()
                ):

                    invalid_reasons.append(

                        f"{club}: {count} players "
                        f"(maximum 3)."
                    )


        # ==================================================
        # INVALID SQUAD
        # ==================================================

        if invalid_reasons:

            st.warning(

                "⚠️ Your selected squad does not "
                "match the standard FPL squad structure."
            )


            for reason in invalid_reasons:

                st.write(
                    f"• {reason}"
                )


            st.info(

                "Your squad should contain exactly "
                "2 GKP, 5 DEF, 5 MID and 3 FWD, "
                "with no more than 3 players from "
                "one club."
            )


        # ==================================================
        # VALID SQUAD
        # ==================================================

        else:

            st.success(

                f"✅ Valid FPL squad structure — "
                f"current player value: "
                f"£{total_current_value:.1f}m"
            )


            st.caption(

                "ℹ️ Current player value can be above "
                "£100m because player prices may have "
                "risen since you bought them."
            )


            # ==================================================
            # TRANSFER SEARCH
            # ==================================================

            if st.button(

                "🔍 Find Best Transfers",

                type="primary"
            ):

                with st.spinner(

                    "Analyzing affordable transfers..."
                ):

                    transfer_df = (

                        find_transfer_suggestions(

                            df,

                            current_squad,

                            bank=bank,

                            budget=100
                        )
                    )


                # ==================================================
                # NO TRANSFERS
                # ==================================================

                if transfer_df.empty:

                    st.info(

                        "No affordable transfers were "
                        "found that improve your projected "
                        "5-GW score."
                    )


                    st.caption(

                        "Try increasing your bank balance "
                        "or check your squad selections."
                    )


                # ==================================================
                # TRANSFERS FOUND
                # ==================================================

                else:

                    st.subheader(

                        "🔥 Best Affordable Transfers"
                    )


                    transfer_display = [

                        "Sell",

                        "Buy",

                        "Position",

                        "Current Score",

                        "New Score",

                        "Gain",

                        "Price Change (£m)",

                        "Required From Bank (£m)",

                        "Bank After Transfer (£m)",

                        "New Club"
                    ]


                    transfer_df[
                        "Position"
                    ] = (

                        transfer_df[
                            "Position"
                        ]

                        .map(
                            position_names
                        )

                        .fillna(
                            transfer_df[
                                "Position"
                            ]
                        )
                    )


                    st.dataframe(

                        transfer_df.head(10)[
                            transfer_display
                        ],

                        use_container_width=True,

                        hide_index=True
                    )


                    # ==================================================
                    # BEST TRANSFER
                    # ==================================================

                    best_transfer = (

                        transfer_df.iloc[0]
                    )


                    price_change = (

                        best_transfer[
                            "Price Change (£m)"
                        ]
                    )


                    if price_change > 0:

                        price_text = (

                            f"+£"
                            f"{price_change:.1f}m"
                        )


                    elif price_change < 0:

                        price_text = (

                            f"-£"
                            f"{abs(price_change):.1f}m"
                        )


                    else:

                        price_text = "£0.0m"


                    required_from_bank = (

                        best_transfer[
                            "Required From Bank (£m)"
                        ]
                    )


                    bank_after = (

                        best_transfer[
                            "Bank After Transfer (£m)"
                        ]
                    )


                    st.success(

                        f"🔥 Best affordable transfer: "

                        f"{best_transfer['Sell']} → "

                        f"{best_transfer['Buy']}  |  "

                        f"+{best_transfer['Gain']:.2f} "
                        f"projected points  |  "

                        f"Bank needed: "
                        f"£{required_from_bank:.1f}m  |  "

                        f"Bank left: "
                        f"£{bank_after:.1f}m"
                    )


                    # ==================================================
                    # WHY THIS TRANSFER?
                    # ==================================================

                    st.subheader(

                        "💡 Why this transfer?"
                    )


                    st.write(

                        f"**Sell:** "
                        f"{best_transfer['Sell']}  \n"

                        f"**Buy:** "
                        f"{best_transfer['Buy']}  \n"

                        f"**5GW score:** "
                        f"{best_transfer['Current Score']:.2f}"
                        f" → "
                        f"{best_transfer['New Score']:.2f}  \n"

                        f"**Projected improvement:** "
                        f"+{best_transfer['Gain']:.2f} points  \n"

                        f"**Price change:** "
                        f"{price_text}  \n"

                        f"**Required from bank:** "
                        f"£{required_from_bank:.1f}m  \n"

                        f"**Bank remaining:** "
                        f"£{bank_after:.1f}m"
                    )


# ==================================================
# FOOTER
# ==================================================

st.divider()


st.caption(

    "FPL 5-Gameweek Optimizer • "
    "Live player and fixture data from "
    "the official Fantasy Premier League API."
)
