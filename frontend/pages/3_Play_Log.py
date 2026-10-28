import streamlit as st
from api_client import (
    ApiError,
    my_games,
    list_sessions,
    end_session,
    update_notes,
    update_rating,
    delete_session,
    list_questions,
    update_rating,
)
from ui import format_timestamp, game_image, live_timer, minutes_played

st.set_page_config(page_title="Play Log", page_icon="📓")

if st.session_state.get("token") is None:
    st.warning("Please log in on the home page.")
    st.stop()  # nothing below this line runs

token = st.session_state["token"]
st.title("Play Log")

# Modular toast feature to add wherever needed
toast_message = st.session_state.pop("toast_message", None)
if toast_message:
    st.toast(toast_message, icon="✅")

try:
    shelf = my_games(token)
    titles = {e["game"]["id"]: e["game"]["title"] for e in shelf}
    ratings = {e["game"]["id"]: e["rating"] for e in shelf}
    sessions = list_sessions(token)
except ApiError as error:
    st.error(error.message)
    st.stop()

selected_game = st.selectbox(
    "Game",
    ["All games", *titles.keys()],
    format_func=lambda game_id: (
        "All games" if game_id == "All games" else titles[game_id]
    ),
)

if selected_game != "All games":
    sessions = [s for s in sessions if s["game_id"] == selected_game]

in_progress = [s for s in sessions if s["ended_at"] is None]
finished = [s for s in sessions if s["ended_at"] is not None]


# Create the containers with game information
def render_session(session):
    session_id = session["id"]
    game_title = titles.get(session["game_id"], "Unknown game")
    with st.container(border=True):
        col_image, col_info = st.columns([1, 5])
        image_path = game_image(game_title)
        if image_path:
            col_image.image(image_path, width="stretch")
        col_info.subheader(game_title)
        col_info.caption(f"Started {format_timestamp(session['started_at'])}")
        if session["ended_at"] is None:
            live_timer(session["started_at"])
            end_col, ask_col = col_info.columns(2)
            if end_col.button("End session", key=f"stop_{session_id}"):
                try:
                    end_session(token, session_id)
                    st.session_state["toast_message"] = (
                        f"{game_title} play session ended"
                    )
                    st.rerun()
                except ApiError as error:
                    st.error(error.message)
            ask_col.page_link(
                "pages/2_Ask_RuleKeepr.py",
                label="Ask RuleKeepr",
                icon="🎲",
            )
        else:
            col_info.caption(f"Ended {format_timestamp(session['ended_at'])}")
            col_info.caption(f"Played {minutes_played(session)} min")
        st.divider()
        if session["ended_at"]:
            current_rating = ratings.get(session["game_id"]) or 0
            with st.form(key=f"rating_form_{session_id}"):
                new_rating = st.slider(
                    f"Rate {game_title} (0 = no rating)",
                    min_value=0.0,
                    max_value=5.0,
                    step=0.25,
                    value=float(current_rating),
                )
                rate_button = st.form_submit_button("Save rating")
            if rate_button:
                try:
                    # The slider's 0 means "no rating"; the API clears it with null.
                    update_rating(token, session["game_id"], new_rating or None)
                except ApiError as error:
                    st.error(error.message)
                else:
                    st.session_state["toast_message"] = (
                        f"{game_title} rated {new_rating} ⭐"
                        if new_rating
                        else f"{game_title} rating cleared"
                    )
                    st.rerun()

        with st.form(key=f"notes_form_{session_id}"):
            note_input = st.text_area(
                label="Notes",
                value=session["notes"] or "",
                max_chars=2000,
                height=150,
            )
            save_button = st.form_submit_button(label="Save notes")
        if save_button:
            if not note_input.strip():
                st.error("Enter something in the notes before saving.")
            else:
                try:
                    update_notes(token, session_id, note_input)
                except ApiError as error:
                    st.error(error.message)
                else:
                    # Rerun so the text area is rebuilt with the saved notes as its default.
                    # Otherwise the changed default resets the box on the next save.
                    st.session_state["toast_message"] = "Notes saved."
                    st.rerun()


tab1, tab2 = st.tabs(
    [f"In Progress ({len(in_progress)})", f"Finished ({len(finished)})"]
)
with tab1:
    if not in_progress:
        st.info("No play sessions in progress.")
    for session in in_progress:
        render_session(session)
with tab2:
    if not finished:
        st.info("No finished play sessions yet.")
    for session in finished:
        render_session(session)
