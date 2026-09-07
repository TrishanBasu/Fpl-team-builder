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

    st.success(
        f"Player dataset loaded successfully — {len(df)} players"
    )

except Exception as e:

    st.error("Could not load the player dataset.")
    st.error(str(e))
    st.stop()


# ==================================================
# LOAD OFFICIAL FPL API
# ==================================================

try:

    fpl_data = get_fpl_data()
    fixtures = get_fixtures()

    st.success("Official FPL data connected successfully!")

except Exception as e:

    st.error("Could not connect to the official FPL API.")
    st.error(str(e))
    st.stop()


# ==================================================
# FIND NEXT 5 GAMEWEEKS
# ==================================================

next_5_gws = get_next_5_gameweeks(fixtures)

if len(next_5_gws) == 0:

    st.warning("No upcoming Gameweeks found.")

else:

    st.subheader("📅 Next 5 Gameweeks")

    gw_text = " → ".join(
        [f"GW {gw}" for gw in next_5_gws]
    )

    st.info(gw_text)


# ==================================================
# CREATE TEAM ID → TEAM NAME
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
# CALCULATE PLAYER FIXTURE DIFFICULTY
# ==================================================

fixture_scores = []


for _, player in df.iterrows():

    # IMPORTANT:
    # Your CSV uses "club_name"

    club_name = player["club_name"]

    team_id = None

    # Find the FPL team ID
    for team in fpl_data["teams"]:

        if team["name"] == club_name:

            team_id = team["id"]

            break


    # Calculate average difficulty
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


# Add difficulty to player data

df["5GW Avg Difficulty"] = fixture_scores


# ==================================================
# PLAYER FIXTURE OUTLOOK
# ==================================================

st.subheader("📊 Player Fixture Outlook")


display_columns = [

    "player_name",

    "club_name",

    "position_name",

    "now_cost",

    "total_points",

    "form",

    "points_per_game",

    "expected_goals",

    "expected_assists",

    "5GW Avg Difficulty"
]


# Keep only columns that exist

available_columns = [

    column

    for column in display_columns

    if column in df.columns
]


# Sort by easiest fixtures

fixture_view = (

    df[available_columns]

    .sort_values(
        "5GW Avg Difficulty",
        na_position="last"
    )

    .head(30)
)


st.dataframe(
    fixture_view,
    use_container_width=True,
    hide_index=True
)


# ==================================================
# SUCCESS
# ==================================================

st.success(
    "✅ Next 5 Gameweeks and player fixture difficulty calculated!"
)
