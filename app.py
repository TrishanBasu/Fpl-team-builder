import streamlit as st
import pandas as pd

from fpl_api import get_fpl_data, get_fixtures, get_next_5_gameweeks


# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

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


# --------------------------------------------------
# LOAD KAGGLE PLAYER DATA
# --------------------------------------------------

df = pd.read_csv("fpl_player_statistics.csv")

st.success(f"Player dataset loaded — {len(df)} players")


# --------------------------------------------------
# LOAD OFFICIAL FPL API
# --------------------------------------------------

try:
    fpl_data = get_fpl_data()
    fixtures = get_fixtures()

    st.success("Official FPL data connected successfully!")

except Exception as e:
    st.error("Could not connect to the official FPL API.")
    st.stop()


# --------------------------------------------------
# FIND NEXT 5 GAMEWEEKS
# --------------------------------------------------

next_5_gws = get_next_5_gameweeks(fixtures)


if len(next_5_gws) < 5:
    st.warning("Less than 5 upcoming Gameweeks were found.")

else:
    st.subheader("📅 Next 5 Gameweeks")

    gw_text = " → ".join([f"GW {gw}" for gw in next_5_gws])

    st.info(gw_text)


# --------------------------------------------------
# SHOW UPCOMING FIXTURES
# --------------------------------------------------

teams = {
    team["id"]: team["name"]
    for team in fpl_data["teams"]
}


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
            "Home Difficulty": fixture["team_h_difficulty"],
            "Away Difficulty": fixture["team_a_difficulty"]
        })


fixture_df = pd.DataFrame(upcoming_fixtures)


st.subheader("🗓️ Upcoming Fixtures")

st.dataframe(
    fixture_df,
    use_container_width=True,
    hide_index=True
)


# --------------------------------------------------
# PLAYER DATA PREVIEW
# --------------------------------------------------

st.subheader("👤 Player Data")

st.dataframe(
    df.head(10),
    use_container_width=True,
    hide_index=True
)
