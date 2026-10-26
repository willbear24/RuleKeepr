from collections import Counter

import streamlit as st

from api_client import (
    ApiError,
    register,
    login,
    get_me,
    my_games,
    list_sessions,
    list_games,
    add_to_shelf,
)

st.set_page_config(page_title="RuleKeepr", page_icon="🎲")
st.title("RuleKeepr")

# --- Session State Init ---
if "token" not in st.session_state:
    st.session_state["token"] = None
if "user" not in st.session_state:
    st.session_state["user"] = None
if "messages" not in st.session_state:
    st.session_state["messages"] = None

# --- Auth Gate ---
if st.session_state["token"] is None:
    register_tab, login_tab = st.tabs(["Register", "Login"])

    with register_tab:
        st.title("RuleKeepr - Register")
        with st.form("Register a new user"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            password = st.text_input("Password (8 char min)", type="password")
            password_confirmation = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Register")
            if submitted:
                if password != password_confirmation:
                    st.error("Passwords do not match.")
                else:
                    try:
                        access_token = register(name, email, password)
                        st.session_state["user"] = get_me(access_token)
                        st.session_state["token"] = access_token
                        st.rerun()
                    except ApiError as error:
                        if error.status_code == 409:
                            st.error("A user with that email already exists.")
                        else:
                            st.error(error.message)

    with login_tab:
        st.title("🔐 RuleKeepr - Login")
        with st.form("Login existing user"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                try:
                    access_token = login(email, password)
                    st.session_state["user"] = get_me(access_token)
                    st.session_state["token"] = access_token
                    st.rerun()
                except ApiError as error:
                    if error.status_code == 401:
                        st.error("Invalid email or password.")
                    else:
                        st.error(error.message)

    st.stop()

# --- Sidebar ---
with st.sidebar:
    user = st.session_state["user"]
    st.write(f"Logged in as **{user['name']}**")
    st.caption(user["email"])
    if st.button("Logout"):
        st.session_state["token"] = None
        st.session_state["user"] = None
        st.rerun()


# --- Dashboard ---
st.subheader("RuleKeepr knows the rules, so you can rule the game")

token = st.session_state["token"]

try:
    shelf = my_games(token)
    sessions = list_sessions(token)
except ApiError as error:
    st.error(error.message)
    st.stop()

in_progress = [s for s in sessions if s["ended_at"] is None]

# Count sessions per game, then look the winner's title up on the shelf.
titles = {entry["game"]["id"]: entry["game"]["title"] for entry in shelf}
play_counts = Counter(s["game_id"] for s in sessions)
if play_counts:
    top_game_id, top_count = play_counts.most_common(1)[0]
    most_played = titles.get(top_game_id, "Unknown")
    most_played_note = f"{top_count} session{'s' if top_count != 1 else ''}"
else:
    most_played, most_played_note = "None yet", None

col1, col2, col3, col4 = st.columns(4)
col1.metric("Games on shelf", len(shelf))
col2.metric("Sessions logged", len(sessions))
col3.metric("In progress", len(in_progress))
col4.metric("Most played", most_played, most_played_note, delta_color="off")

# --- Add games ---
st.divider()
st.subheader("Add a game to your shelf")

# Set before st.rerun() on a successful add; shown once, then cleared.
added_title = st.session_state.pop("added_game", None)
if added_title:
    st.success(f"{added_title} was added to your shelf!")

try:
    catalog = list_games(token)
except ApiError as error:
    st.error(error.message)
    st.stop()

on_shelf = {entry["game"]["id"] for entry in shelf}  # reuse `shelf` from the metrics
available = [g for g in catalog if g["id"] not in on_shelf]

if not available:
    st.info("Every game in the catalog is already on your shelf.")
else:
    for game in available:
        col_info, col_btn = st.columns([4, 1])
        col_info.markdown(f"**{game['title']}**")
        col_info.caption(
            f"{game['min_player']}-{game['max_player']} players · {game['play_time_minutes']} min"
        )
        if col_btn.button("Add", key=f"add_{game['id']}"):
            try:
                add_to_shelf(token, game["id"])
                st.session_state["added_game"] = game["title"]
                st.rerun()
            except ApiError as error:
                st.error(error.message)
