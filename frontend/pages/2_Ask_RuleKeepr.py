import streamlit as st

from api_client import ApiError, ask_question, list_questions, list_sessions, my_games
from ui import format_timestamp

st.set_page_config(page_title="Ask RuleKeepr", page_icon="🎲")

if st.session_state.get("token") is None:
    st.warning("Please log in on the home page.")
    st.stop()

token = st.session_state["token"]
st.title("Ask RuleKeepr")

try:
    shelf = my_games(token)
    sessions = list_sessions(token)
except ApiError as error:
    st.error(error.message)
    st.stop()

titles = {entry["game"]["id"]: entry["game"]["title"] for entry in shelf}
in_progress = {s["id"]: s for s in sessions if s["ended_at"] is None}

if not in_progress:
    st.info(
        "Questions can only be asked during a play session. Start one from My Gameshelf."
    )
    st.page_link("pages/1_My_Gameshelf.py", label="Go to My Gameshelf")
    st.stop()


def describe_session(session_id):
    session = in_progress[session_id]
    title = titles.get(session["game_id"], "Unknown game")
    return f"{title} · Started {format_timestamp(session['started_at'])}"


session_id = st.selectbox(
    "Play session", list(in_progress), format_func=describe_session
)

try:
    questions = list_questions(token, session_id)
except ApiError as error:
    st.error(error.message)
    st.stop()

source_history = st.session_state.setdefault("ask_rulekeepr_sources", {})
session_sources = source_history.setdefault(session_id, {})

for item in questions:
    with st.chat_message("user"):
        st.write(item["question_text"])
        st.caption(f"Asked {format_timestamp(item['asked_at'])}")

    with st.chat_message("assistant"):
        st.write(item["answer_text"] or "No answer was generated.")
        if str(item["id"]) in session_sources:
            sources = session_sources[str(item["id"])]
            if sources:
                with st.expander(f"Sources ({len(sources)})"):
                    for chunk in sources:
                        section = chunk["section"] or f"Chunk {chunk['chunk_index']}"
                        st.caption(f"{chunk['game_title']} · {section}")
                        st.write(chunk["text"])
            else:
                st.caption("No matching rulebook excerpts were found.")
        else:
            st.caption("Sources aren't stored with saved question history.")

question = st.chat_input("Ask a question about the rules...", max_chars=2000)
if question:
    with st.spinner("Searching the rulebook..."):
        try:
            answer = ask_question(token, session_id, question)
        except ApiError as error:
            st.error(error.message)
        else:
            session_sources[str(answer["id"])] = answer["sources"]
            st.rerun()
