import streamlit as st
from api_client import ApiError, my_games, remove_from_shelf

st.set_page_config(page_title="My Gameshelf", page_icon="🎲")

if st.session_state.get("token") is None:
    st.warning("Please log in on the home page.")
    st.stop()  # nothing below this line runs

token = st.session_state["token"]
st.title("My Gameshelf")

# Shown here, before any st.stop(), so it also appears when the last game was removed.
removed_title = st.session_state.pop("removed_game", None)
if removed_title:
    st.success(f"{removed_title} was removed from your shelf.")

try:
    shelf = my_games(token)
except ApiError as error:
    st.error(error.message)
    st.stop()

if not shelf:
    st.info("Your shelf is empty. Add games from the home page.")
    st.page_link("Home.py", label="Go to Home")
    st.stop()

for entry in shelf:
    game = entry["game"]
    with st.container(border=True):
        col_info, col_btn = st.columns([4, 1])
        col_info.subheader(game["title"])
        col_info.caption(
            f"{game['min_player']}-{game['max_player']} players · {game['play_time_minutes']} min"
        )
        if col_btn.button("Remove", key=f"remove_{game['id']}"):
            try:
                remove_from_shelf(token, game["id"])
                st.session_state["removed_game"] = game["title"]
                st.rerun()
            except ApiError as error:
                st.error(error.message)
