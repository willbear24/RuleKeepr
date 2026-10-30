import streamlit as st
from api_client import (
    ApiError,
    my_games,
    remove_from_shelf,
    list_sessions,
    create_session,
    end_session,
)
from collections import Counter
from ui import format_play_time, game_image, live_timer, minutes_played

st.set_page_config(page_title="My Gameshelf", page_icon="🎲")

if st.session_state.get("token") is None:
    st.warning("Please log in on the home page.")
    st.stop()  # nothing below this line runs

token = st.session_state["token"]
st.title("My Gameshelf")

toast_message = st.session_state.pop("toast_message", None)
if toast_message:
    st.toast(toast_message, icon="✅")

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

try:
    sessions = list_sessions(token)
except ApiError as error:
    st.error(error.message)
    st.stop()

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


st.subheader("Filter Games")
filtered_games_players = st.selectbox(
    label="Number of Players",
    options=["Any", "1", "2", "3", "4", "5+"],
    index=0,
)
filtered_games_rating = st.selectbox(
    label="Rating",
    options=["Any", "1 ⭐", "2 ⭐", "3 ⭐", "4 ⭐", "5 ⭐"],
    index=0,
)
filter_games_playtime = st.slider(
    label="Average Game Length (maximum)",
    min_value=10,
    max_value=180,
    value=180,
    step=5,
)


def average_minutes(play_time):
    """Midpoint of a play_time_minutes range such as '60-180', or None if missing."""
    if not play_time:
        return None
    bounds = [float(part) for part in play_time.split("-")]
    return sum(bounds) / len(bounds)


def matches_filters(entry):
    game = entry["game"]

    if filtered_games_players == "5+":
        if game["max_player"] is None or game["max_player"] < 5:
            return False
    elif filtered_games_players != "Any":
        players = int(filtered_games_players)
        if game["min_player"] is None or game["max_player"] is None:
            return False
        if not game["min_player"] <= players <= game["max_player"]:
            return False

    # Unrated games are kept so they still show up when a rating filter is set.
    if filtered_games_rating != "Any":
        stars = int(filtered_games_rating[0])
        if entry["rating"] is not None and entry["rating"] < stars:
            return False

    # The slider's maximum means no length limit.
    if filter_games_playtime < 180:
        average = average_minutes(game["play_time_minutes"])
        if average is None or average > filter_games_playtime:
            return False
    return True


shelf_view = [entry for entry in shelf if matches_filters(entry)]
if not shelf_view:
    st.info("No games on your shelf match these filters.")

for entry in shelf_view:
    game = entry["game"]
    game_sessions = counts[game["id"]]
    with st.container(border=True):
        col_image, col_info, col_btn = st.columns([1, 3, 1])
        image_path = game_image(game["title"])
        if image_path:
            col_image.image(image_path, width="stretch")
        col_info.subheader(game["title"])
        col_info.caption(f"{game['min_player']}-{game['max_player']} players")
        if game["play_time_minutes"]:
            col_info.caption(f"Play time: {game['play_time_minutes']} min")
        rating = entry["rating"]
        col_info.caption(
            f"Rating: {rating} ⭐" if rating is not None else "Not rated yet"
        )
        active = next(
            (
                s
                for s in sessions
                if s["game_id"] == game["id"] and s["ended_at"] is None
            ),
            None,
        )
        if active:
            live_timer(active["started_at"])
        metric_sessions, metric_time = col_info.columns(2)
        metric_sessions.metric("Sessions Logged", game_sessions)
        metric_time.metric("Time Played", format_play_time(time_played[game["id"]]))
        if col_btn.button("Remove", key=f"remove_{game['id']}"):
            confirm_remove(game["id"], game["title"], game_sessions)
        if active:
            if col_btn.button("End session", key=f"stop_{active['id']}"):
                try:
                    end_session(token, active["id"])
                    st.session_state["toast_message"] = (
                        f"{game['title']} play session ended"
                    )
                    st.rerun()
                except ApiError as error:
                    st.error(error.message)
        elif col_btn.button("Start Session", key=f"start_{game['id']}"):
            try:
                create_session(token, game["id"])
                st.switch_page("pages/3_Play_Log.py")
            except ApiError as error:
                st.error(error.message)
