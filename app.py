import streamlit as st
import pandas as pd

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

# Load player data
df = pd.read_csv("fpl_player_statistics.csv")

st.success("Player dataset loaded successfully!")

st.write("Number of players:", len(df))

st.dataframe(df.head(10))
