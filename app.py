import streamlit as st
import pandas as pd

from fpl_api import (
    get_fpl_data,
    get_fixtures,
    get_next_5_gameweeks,
    calculate_fixture_difficulty
)

from optimizer import (
    build_best_team,
    find_transfer_suggestions
)


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="FPL 5GW Optimizer",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ FPL 5-Gameweek Optimizer")

st.write(
    "Build the best FPL team or find legal transfer "
    "suggestions based on the next 5 Gameweeks."
)


# ============================================================
# LOAD PLAYER DATA
# ============================================================

try:

    df = pd.read_csv(
        "fpl_player_statistics.csv"
    )

except Exception as e:

    st.error(
        "Could not load player dataset."
    )

    st.error(str(e))

    st.stop()


# ============================================================
# LOAD OFFICIAL FPL API
# ============================================================

try:

    fpl_data = get_fpl_data()

    fixtures = get_fixtures()

except Exception as e:

    st.error(
        "Could not connect to official FPL API."
    )

    st.error(str(e))

    st.stop()


# ============================================================
# NEXT 5 GAMEWEEKS
# ============================================================

next_5_gws = get_next_5_gameweeks(
    fixtures
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


# ============================================================
# TEAM ID LOOKUP
# ============================================================

team_ids = {

    team["name"]: team["id"]

    for team in fpl_data["teams"]
}


# ============================================================
# CALCULATE FIXTURE DIFFICULTY
# ============================================================

fixture_scores = []

for _, player in df.iterrows():

    club_name = player["club_name"]

    team_id = team_ids.get(
        club_name
    )

    if team_id is not None:

        difficulty = (
            calculate_fixture_difficulty(
                fixtures,
                team_id,
                next_5_gws
            )
        )

    else:

        difficulty = None

    fixture_scores.append(
        difficulty
    )


df["5GW Avg Difficulty"] = (
    fixture_scores
)


# ============================================================
# NUMERIC DATA
# ============================================================

numeric_columns = [

    "form",

    "points_per_game",

    "total_points",

    "expected_goals",

    "expected_assists",

    "now_cost"

]


for column in numeric_columns:

    if column in df.columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )


# ============================================================
# PERFORMANCE SCORE
# ============================================================

df["Performance Score"] = (

    df["form"].fillna(0) * 0.35

    +

    df["points_per_game"].fillna(0) * 0.30

    +

    (
        df["total_points"].fillna(0)
        / 10
    ) * 0.20

    +

    df["expected_goals"].fillna(0)
    * 0.075

    +

    df["expected_assists"].fillna(0)
    * 0.075

)


# ============================================================
# FIXTURE FACTOR
# ============================================================

df["Fixture Factor"] = (

    6
    -
    df["5GW Avg Difficulty"].fillna(3)

)


# ============================================================
# FINAL 5GW SCORE
# ============================================================

df["5GW Score"] = (

    df["Performance Score"]
    *
    df["Fixture Factor"]

)


# ============================================================
# MAIN MENU
# ============================================================

st.divider()

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


# ============================================================
# BUILD FULL TEAM
# ============================================================

if option == "🏆 Build Full Team":

    st.subheader(
        "🏆 Best £100m Team"
    )

    st.write(
        "The optimizer selects 15 players while "
        "respecting FPL squad rules."
    )

    if st.button(
        "🚀 Build My Team",
        type="primary"
    ):

        best_team = build_best_team(
            df,
            budget=1000
        )

        if best_team.empty:

            st.error(
                "Could not find a valid £100m squad."
            )

        else:

            best_team["Price (£m)"] = (
                best_team["price"] / 10
            )

            total_cost = (
                best_team["price"].sum()
                / 10
            )

            st.success(
                f"Team found! "
                f"Total cost: £{total_cost:.1f}m"
            )

            position_order = {

                "Goalkeeper": 1,

                "Defender": 2,

                "Midfielder": 3,

                "Forward": 4

            }

            best_team["position_order"] = (
                best_team[
                    "position_name"
                ].map(position_order)
            )

            best_team = (
                best_team
                .sort_values(
                    "position_order"
                )
            )

            display_columns = [

                "player_name",

                "club_name",

                "position_name",

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

            st.subheader(
                "📊 Squad Summary"
            )

            col1, col2, col3 = st.columns(3)

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


# ============================================================
# TRANSFER SUGGESTIONS
# ============================================================

else:

    st.subheader(
        "🔄 Transfer Suggestions"
    )

    st.write(
        "Select your current 15-man squad. "
        "The optimizer will test legal single transfers."
    )

    player_names = sorted(
        df["player_name"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_players = st.multiselect(

        "Select your current squad (15 players)",

        player_names,

        max_selections=15

    )


    # --------------------------------------------------------
    # WAIT UNTIL 15 PLAYERS ARE SELECTED
    # --------------------------------------------------------

    if len(selected_players) < 15:

        st.info(

            f"Select "
            f"{15 - len(selected_players)} "
            f"more player(s)."

        )


    else:

        st.success(
            "✅ 15 players selected!"
        )


        current_squad = df[
            df["player_name"].isin(
                selected_players
            )
        ].copy()


        # ----------------------------------------------------
        # CURRENT SQUAD
        # ----------------------------------------------------

        st.subheader(
            "👥 Your Current Squad"
        )


        current_squad[
            "Price (£m)"
        ] = (
            current_squad["now_cost"]
            / 10
        )


        current_display = [

            "player_name",

            "club_name",

            "position_name",

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


        # ----------------------------------------------------
        # SQUAD VALIDATION
        # ----------------------------------------------------

        position_counts = (
            current_squad[
                "position_name"
            ]
            .value_counts()
        )

        total_cost = (
            current_squad["now_cost"].sum()
            / 10
        )

        club_counts = (
            current_squad["club_name"]
            .value_counts()
        )


        invalid_reasons = []


        if len(current_squad) != 15:

            invalid_reasons.append(
                "Squad must contain exactly 15 players."
            )


        required_positions = {

            "Goalkeeper": 2,

            "Defender": 5,

            "Midfielder": 5,

            "Forward": 3

        }


        for position, required in (
            required_positions.items()
        ):

            actual = position_counts.get(
                position,
                0
            )

            if actual != required:

                invalid_reasons.append(

                    f"{position}: "
                    f"{actual}/{required}"

                )


        if total_cost > 100:

            invalid_reasons.append(

                f"Squad costs £{total_cost:.1f}m "
                f"(over the £100m limit)."

            )


        if not club_counts.empty:

            if club_counts.max() > 3:

                invalid_reasons.append(

                    "You have more than 3 players "
                    "from the same club."

                )


        # ----------------------------------------------------
        # SHOW VALIDATION
        # ----------------------------------------------------

        if invalid_reasons:

            st.warning(
                "⚠️ Your selected squad is not a valid "
                "FPL squad:"
            )

            for reason in invalid_reasons:

                st.write(
                    f"• {reason}"
                )

            st.info(
                "Transfer suggestions require a legal "
                "15-player squad."
            )


        else:

            st.success(
                f"✅ Valid squad — £{total_cost:.1f}m"
            )


            # ------------------------------------------------
            # FIND TRANSFERS
            # ------------------------------------------------

            if st.button(
                "🔍 Find Best Transfers",
                type="primary"
            ):

                with st.spinner(
                    "Analyzing possible transfers..."
                ):

                    transfer_df = (
                        find_transfer_suggestions(
                            df,
                            current_squad,
                            budget=1000
                        )
                    )


                # --------------------------------------------
                # NO RESULTS
                # --------------------------------------------

                if transfer_df.empty:

                    st.info(
                        "No legal transfers found that "
                        "improve your projected 5-GW score."
                    )


                else:

                    st.subheader(
                        "🔥 Best Transfer Suggestions"
                    )


                    transfer_display = [

                        "Sell",

                        "Buy",

                        "Position",

                        "Current Score",

                        "New Score",

                        "Gain",

                        "Price Change (£m)",

                        "New Club"

                    ]


                    st.dataframe(

                        transfer_df.head(10)[
                            transfer_display
                        ],

                        use_container_width=True,

                        hide_index=True

                    )


                    # ----------------------------------------
                    # BEST TRANSFER
                    # ----------------------------------------

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
                            f"+£{price_change:.1f}m"
                        )

                    elif price_change < 0:

                        price_text = (
                            f"-£{abs(price_change):.1f}m"
                        )

                    else:

                        price_text = "£0.0m"


                    st.success(

                        f"🔥 Best transfer: "
                        f"{best_transfer['Sell']} → "
                        f"{best_transfer['Buy']}  |  "
                        f"+{best_transfer['Gain']:.2f} "
                        f"projected points  |  "
                        f"{price_text}"

                    )


                    # ----------------------------------------
                    # EXPLANATION
                    # ----------------------------------------

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
                        f"{price_text}"

                    )
