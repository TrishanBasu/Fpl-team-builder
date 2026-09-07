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

    df = pd.read_csv("fpl_player_statistics.csv")

except Exception as e:

    st.error("Could not load player dataset.")
    st.error(str(e))
    st.stop()


# ==================================================
# LOAD OFFICIAL FPL API
# ==================================================

try:

    fpl_data = get_fpl_data()
    fixtures = get_fixtures()

except Exception as e:

    st.error("Could not connect to official FPL API.")
    st.error(str(e))
    st.stop()


# ==================================================
# NEXT 5 GAMEWEEKS
# ==================================================

next_5_gws = get_next_5_gameweeks(fixtures)

st.subheader("📅 Next 5 Gameweeks")

if next_5_gws:

    st.info(
        " → ".join(
            [f"GW {gw}" for gw in next_5_gws]
        )
    )

else:

    st.warning("No upcoming Gameweeks found.")


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

        difficulty = calculate_fixture_difficulty(
            fixtures,
            team_id,
            next_5_gws
        )

    else:

        difficulty = None


    fixture_scores.append(difficulty)


df["5GW Avg Difficulty"] = fixture_scores


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
        df["total_points"].fillna(0) / 10
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

    6 -
    df["5GW Avg Difficulty"].fillna(3)

)


# ==================================================
# FINAL 5GW SCORE
# ==================================================

df["5GW Score"] = (

    df["Performance Score"] *
    df["Fixture Factor"]

)


# ==================================================
# MAIN MENU
# ==================================================

st.divider()

st.header("What do you want to do?")


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

    st.subheader("🏆 Best £100m Team")

    st.write(
        "The optimizer selects 15 players using "
        "the next-5-GW score."
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
                best_team["price"].sum() / 10
            )


            st.success(
                f"Team found! Total cost: "
                f"£{total_cost:.1f}m"
            )


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
                .sort_values("position_order")
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
                best_team[display_columns],
                use_container_width=True,
                hide_index=True
            )


# ==================================================
# TRANSFER SUGGESTIONS
# ==================================================

else:

    st.subheader("🔄 Transfer Suggestions")

    st.write(
        "Select your current 15-man squad. "
        "We'll look for better players for the "
        "next 5 Gameweeks."
    )


    # --------------------------------------------------
    # PLAYER LIST
    # --------------------------------------------------

    player_names = sorted(
        df["player_name"]
        .dropna()
        .unique()
        .tolist()
    )


    # --------------------------------------------------
    # SELECT 15 PLAYERS
    # --------------------------------------------------

    selected_players = st.multiselect(

        "Select your current squad (15 players)",

        player_names,

        max_selections=15

    )


    # --------------------------------------------------
    # CHECK SQUAD
    # --------------------------------------------------

    if len(selected_players) < 15:

        st.info(
            f"Select {15 - len(selected_players)} "
            "more player(s) to analyze your squad."
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


        # --------------------------------------------------
        # CURRENT SQUAD
        # --------------------------------------------------

        st.subheader("👥 Your Current Squad")


        current_display = [

            "player_name",
            "club_name",
            "position_name",
            "now_cost",
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


        # --------------------------------------------------
        # FIND TRANSFERS
        # --------------------------------------------------

        transfer_results = []


        for _, current_player in (
            current_squad.iterrows()
        ):

            current_name = (
                current_player["player_name"]
            )

            current_position = (
                current_player["position_name"]
            )

            current_score = float(
                current_player["5GW Score"]
            )

            current_price = float(
                current_player["now_cost"]
            )


            # Same position only
            alternatives = df[
                (
                    df["position_name"]
                    ==
                    current_position
                )
                &
                (
                    ~df["player_name"]
                    .isin(selected_players)
                )
            ].copy()


            if alternatives.empty:
                continue


            # Score improvement
            alternatives[
                "Score Improvement"
            ] = (

                alternatives["5GW Score"]
                -
                current_score

            )


            # Price difference
            alternatives[
                "Price Difference (£m)"
            ] = (

                (
                    alternatives["now_cost"]
                    -
                    current_price
                )
                / 10

            )


            # Only better players
            alternatives = alternatives[
                alternatives[
                    "Score Improvement"
                ] > 0
            ]


            if alternatives.empty:
                continue


            # Best replacement
            best = (
                alternatives
                .sort_values(
                    "Score Improvement",
                    ascending=False
                )
                .iloc[0]
            )


            transfer_results.append({

                "Sell": current_name,

                "Buy": best["player_name"],

                "Position": current_position,

                "Current Score":
                    round(
                        current_score,
                        2
                    ),

                "New Score":
                    round(
                        best["5GW Score"],
                        2
                    ),

                "Gain":
                    round(
                        best[
                            "Score Improvement"
                        ],
                        2
                    ),

                "Price Change (£m)":
                    round(
                        best[
                            "Price Difference (£m)"
                        ],
                        1
                    )

            })


        # --------------------------------------------------
        # TRANSFER TABLE
        # --------------------------------------------------

        st.subheader(
            "🔥 Recommended Transfers"
        )


        if not transfer_results:

            st.info(
                "No better replacements found."
            )

        else:

            transfer_df = pd.DataFrame(
                transfer_results
            )


            transfer_df = (
                transfer_df
                .sort_values(
                    "Gain",
                    ascending=False
                )
                .head(10)
            )


            st.dataframe(

                transfer_df,

                use_container_width=True,

                hide_index=True

            )


            best_transfer = (
                transfer_df.iloc[0]
            )


            st.success(

                f"🔥 Best transfer: "
                f"{best_transfer['Sell']} → "
                f"{best_transfer['Buy']} "
                f"({best_transfer['Gain']:+.2f} "
                f"projected points)"

            )
