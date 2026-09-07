import streamlit as st
import pandas as pd

from fpl_api import (
    get_fpl_data,
    get_fixtures,
    get_next_5_gameweeks,
    calculate_fixture_difficulty
)

from optimizer import build_best_team


# ==================================================
# PAGE SETUP
# ==================================================

st.set_page_config(
    page_title="FPL 5GW Optimizer",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ FPL 5-Gameweek Optimizer")

st.write(
    "Build the best FPL team or find transfer suggestions "
    "based on the next 5 Gameweeks."
)


# ==================================================
# LOAD PLAYER DATA
# ==================================================

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


# ==================================================
# LOAD FPL API
# ==================================================

try:

    fpl_data = get_fpl_data()

    fixtures = get_fixtures()

except Exception as e:

    st.error(
        "Could not connect to official FPL API."
    )

    st.error(str(e))

    st.stop()


# ==================================================
# NEXT 5 GAMEWEEKS
# ==================================================

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


# ==================================================
# TEAM MAPPING
# ==================================================

teams = {
    team["id"]: team["name"]
    for team in fpl_data["teams"]
}


# ==================================================
# CALCULATE FIXTURE DIFFICULTY
# ==================================================

fixture_scores = []


for _, player in df.iterrows():

    club_name = player["club_name"]

    team_id = None

    for team in fpl_data["teams"]:

        if team["name"] == club_name:

            team_id = team["id"]

            break


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


# ==================================================
# NUMERIC DATA
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

    if column in df.columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )


# ==================================================
# PERFORMANCE SCORE
# ==================================================

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

    df["expected_goals"].fillna(0) * 0.075

    +

    df["expected_assists"].fillna(0) * 0.075

)


# ==================================================
# FIXTURE FACTOR
# ==================================================

df["Fixture Factor"] = (

    6
    -
    df["5GW Avg Difficulty"].fillna(3)

)


# ==================================================
# FINAL 5GW SCORE
# ==================================================

df["5GW Score"] = (

    df["Performance Score"]

    *

    df["Fixture Factor"]

)


# ==================================================
# MAIN OPTIONS
# ==================================================

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


# ==================================================
# BUILD FULL TEAM
# ==================================================

if option == "🏆 Build Full Team":

    st.subheader(
        "🏆 Best £100m Team"
    )

    st.write(
        "The optimizer will select 15 players "
        "based on their projected 5-GW score."
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

            # Convert price to millions
            best_team["Price (£m)"] = (
                best_team["price"] / 10
            )


            # Total cost
            total_cost = (
                best_team["price"].sum()
                / 10
            )


            st.success(
                f"Team found! Total cost: "
                f"£{total_cost:.1f}m"
            )


            # Position order
            position_order = {

                "Goalkeeper": 1,

                "Defender": 2,

                "Midfielder": 3,

                "Forward": 4
            }


            best_team["position_order"] = (
                best_team["position_name"]
                .map(position_order)
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


            # Position summary
            st.subheader(
                "📋 Squad Summary"
            )


            position_counts = (
                best_team[
                    "position_name"
                ]
                .value_counts()
            )


            col1, col2, col3, col4 = (
                st.columns(4)
            )


            col1.metric(
                "🧤 GK",
                position_counts.get(
                    "Goalkeeper",
                    0
                )
            )

            col2.metric(
                "🛡️ DEF",
                position_counts.get(
                    "Defender",
                    0
                )
            )

            col3.metric(
                "⚽ MID",
                position_counts.get(
                    "Midfielder",
                    0
                )
            )

            col4.metric(
                "🎯 FWD",
                position_counts.get(
                    "Forward",
                    0
                )
            )


# ==================================================
# TRANSFER SUGGESTIONS
# ==================================================

else:

    st.subheader(
        "🔄 Transfer Suggestions"
    )

    st.info(
        "Transfer mode will be added in the next step."
    )
