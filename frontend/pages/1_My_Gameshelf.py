import streamlit as st
from api_client import (
    ApiError,
    my_games,
    remove_from_shelf,
    list_sessions,
    create_session,
)
from collections import Counter
from ui import game_image, minutes_played

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

sessions = list_sessions(token)
counts = Counter(s["game_id"] for s in sessions)
time_played = Counter()
for s in sessions:
    minutes = minutes_played(s)
    if minutes is not None:
        time_played[s["game_id"]] += minutes


@st.dialog("Remove game?", icon="🚨")
def confirm_remove(game_id, title, session_count):
    st.write(f"Remove **{title}** from your shelf?")
    st.warning(
        f"This also deletes its {session_count} logged play session(s) "
        "and their questions. It can't be undone."
    )
    confirm_col, cancel_col = st.columns(2)
    if confirm_col.button("Yes, remove", type="primary", width="stretch"):
        try:
            remove_from_shelf(token, game_id)
        except ApiError as error:
            st.error(error.message)
            return
        st.session_state["removed_game"] = title
        st.rerun()
    if cancel_col.button("Cancel", width="stretch"):
        st.rerun()


for entry in shelf:
    game = entry["game"]
    game_sessions = counts[game["id"]]
    with st.container(border=True):
        col_image, col_info, col_btn = st.columns([1, 3, 1])
        image_path = game_image(game["title"])
        if image_path:
            col_image.image(image_path, width="stretch")
        col_info.subheader(game["title"])
        col_info.caption(f"{game['min_player']}-{game['max_player']} players")
        rating = entry["rating"]
        col_info.caption(
            f"Rating: {rating} ⭐" if rating is not None else "Not rated yet"
        )
        metric_sessions, metric_time = col_info.columns(2)
        metric_sessions.metric("Sessions Logged", game_sessions)
        metric_time.metric("Time Played", f"{time_played[game['id']]} min")
        if col_btn.button("Remove", key=f"remove_{game['id']}"):
            confirm_remove(game["id"], game["title"], game_sessions)
        if col_btn.button("Start Session", key=f"start_{game['id']}"):
            try:
                create_session(token, game["id"])
                st.switch_page("pages/3_Play_Log.py")
            except ApiError as error:
                st.error(error.message)
