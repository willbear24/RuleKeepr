import streamlit as st
from api_client import ApiError, list_games  # whatever the page needs

st.set_page_config(page_title="Play Log", page_icon="🎲")

if st.session_state.get("token") is None:
    st.warning("Please log in on the home page.")
    st.stop()  # nothing below this line runs

token = st.session_state["token"]
st.title("Play Log")
# ...page content...
