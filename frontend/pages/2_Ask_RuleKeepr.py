import streamlit as st
from api_client import ApiError, ask_question, list_questions, list_sessions, my_games

st.set_page_config(page_title="Ask RuleKeepr", page_icon="🎲")

if st.session_state.get("token") is None:
    st.warning("Please log in on the home page.")
    st.stop()  # nothing below this line runs

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
    return f"{title} · started {session['started_at']} UTC"


session_id = st.selectbox(
    "Play session", list(in_progress), format_func=describe_session
)

with st.form("ask_form"):
    question = st.text_area("Your question", max_chars=2000)
    submitted = st.form_submit_button("Ask")

if submitted:
    if not question.strip():
        st.warning("Type a question first.")
    else:
        with st.spinner("Searching the rulebook..."):
            try:
                answer = ask_question(token, session_id, question)
            except ApiError as error:
                st.error(error.message)
            else:
                st.session_state["last_answer"] = {
                    "session_id": session_id,
                    "answer": answer,
                }

# Sources are only returned when a question is asked, so keep the latest answer.
last = st.session_state.get("last_answer")
if last and last["session_id"] == session_id:
    answer = last["answer"]
    st.subheader("Answer")
    st.write(answer["answer_text"] or "No answer was generated.")
    sources = answer["sources"]
    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for chunk in sources:
                section = chunk["section"] or f"Chunk {chunk['chunk_index']}"
                st.markdown(f"**{chunk['game_title']}** · {section}")
                st.text(chunk["text"])

st.divider()
st.subheader("Previous questions")
try:
    questions = list_questions(token, session_id)
except ApiError as error:
    st.error(error.message)
    st.stop()

if not questions:
    st.info("No questions asked in this session yet.")
for item in reversed(questions):
    with st.container(border=True):
        st.markdown(f"**Q:** {item['question_text']}")
        st.write(item["answer_text"] or "_No answer saved._")
