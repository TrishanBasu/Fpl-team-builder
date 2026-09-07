import streamlit as st
import pandas as pd

from fpl_api import (
    get_fpl_data,
    get_fixtures,
    get_next_5_gameweeks,
    calculate_fixture_difficulty
)


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


st.success(
    f"Player dataset loaded — {len(df)} players"
)


# ==================================================
# LOAD OFFICIAL FPL DATA
# ==================================================

try:

    fpl_data = get_fpl_data()
    fixtures = get_fixtures()

except Exception as e:

    st.error("Could not connect to the official FPL API.")
    st.error(str(e))
    st.stop()


st.success(
    "Official FPL data connected successfully!"
)


# ==================================================
# FIND NEXT 5 GAMEWEEKS
# ==================================================

next_5_gws = get_next_5_gameweeks(fixtures)


st.subheader("📅 Next 5 Gameweeks")

if next_5_gws:

    gw_text = " → ".join(
        [f"GW {gw}" for gw in next_5_gws]
    )

    st.info(gw_text)

else:

    st.warning("No upcoming Gameweeks found.")


# ==================================================
# TEAM MAPPING
# ==================================================

teams = {
    team["id"]: team["name"]
    for team in fpl_data["teams"]
}


# ==================================================
# UPCOMING FIXTURES
# ==================================================

upcoming_fixtures = []


for fixture in fixtures:

    if (
        fixture["event"] in next_5_gws
        and not fixture["finished"]
    ):

        home_team = teams.get(
            fixture["team_h"],
            "Unknown"
        )

        away_team = teams.get(
            fixture["team_a"],
            "Unknown"
        )

        upcoming_fixtures.append({

            "Gameweek": fixture["event"],

            "Home": home_team,

            "Away": away_team,

            "Home Difficulty":
                fixture["team_h_difficulty"],

            "Away Difficulty":
                fixture["team_a_difficulty"]
        })


fixture_df = pd.DataFrame(
    upcoming_fixtures
)


st.subheader("🗓️ Upcoming Fixtures")


if not fixture_df.empty:

    st.dataframe(
        fixture_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("No upcoming fixtures found.")


# ==================================================
# CALCULATE 5-GW FIXTURE DIFFICULTY
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

        avg_difficulty = calculate_fixture_difficulty(
            fixtures,
            team_id,
            next_5_gws
        )

    else:

        avg_difficulty = None


    fixture_scores.append(
        avg_difficulty
    )


df["5GW Avg Difficulty"] = fixture_scores


# ==================================================
# CLEAN NUMERIC DATA
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
# CREATE PERFORMANCE SCORE
# ==================================================

df["Performance Score"] = (

    df["form"].fillna(0) * 0.35

    +

    df["points_per_game"].fillna(0) * 0.30

    +

    (
        df["total_points"].fillna(0)
        /
        10
    ) * 0.20

    +

    df["expected_goals"].fillna(0) * 0.075

    +

    df["expected_assists"].fillna(0) * 0.075

)


# ==================================================
# CREATE FIXTURE FACTOR
# ==================================================

df["Fixture Factor"] = (

    6 - df["5GW Avg Difficulty"].fillna(3)

)


# ==================================================
# CREATE FINAL 5-GW SCORE
# ==================================================

df["5GW Score"] = (

    df["Performance Score"]

    *

    df["Fixture Factor"]

)


# ==================================================
# PLAYER RANKING
# ==================================================

st.subheader("🏆 Best Players for the Next 5 GWs")


ranking_columns = [

    "player_name",

    "club_name",

    "position_name",

    "now_cost",

    "form",

    "points_per_game",

    "expected_goals",

    "expected_assists",

    "5GW Avg Difficulty",

    "5GW Score"
]


available_columns = [

    column

    for column in ranking_columns

    if column in df.columns

]


ranked_players = (

    df[available_columns]

    .sort_values(
        "5GW Score",
        ascending=False
    )

    .head(30)

)


st.dataframe(
    ranked_players,
    use_container_width=True,
    hide_index=True
)


# ==================================================
# POSITION FILTER
# ==================================================

st.subheader("🔎 Filter Players")

selected_position = st.selectbox(
    "Choose a position",
    [
        "All",
        "Goalkeeper",
        "Defender",
        "Midfielder",
        "Forward"
    ]
)


if selected_position != "All":

    filtered_players = df[
        df["position_name"] == selected_position
    ]

else:

    filtered_players = df


filtered_players = (

    filtered_players

    .sort_values(
        "5GW Score",
        ascending=False
    )

    .head(30)

)


st.dataframe(
    filtered_players[available_columns],
    use_container_width=True,
    hide_index=True
)


# ==================================================
# SUCCESS
# ==================================================

st.success(
    "✅ 5-GW player scores calculated successfully!"
)
