from datetime import datetime
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).parent / "assets" / "games"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def game_image(title):
    """Return the image path for a game title, or None if there isn't one.

    Files are named after the title in lowercase with underscores,
    e.g. "Settlers of Catan" -> settlers_of_catan.png
    """
    name = title.lower().replace(" ", "_")
    for ext in IMAGE_EXTENSIONS:
        path = ASSETS / f"{name}{ext}"
        if path.exists():
            return str(path)
    return None


def format_timestamp(value):
    """Format an API timestamp (naive UTC) in local time, e.g. 'Oct 27, 2026 12:42 PM'."""
    utc = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    return utc.astimezone().strftime("%b %d, %Y %-I:%M %p")


def minutes_played(session):
    """Whole minutes between a session's start and end, or None if it's still running."""
    if session["ended_at"] is None:
        return None
    started = datetime.fromisoformat(session["started_at"])
    ended = datetime.fromisoformat(session["ended_at"])
    return round((ended - started).total_seconds() / 60)


def total_minutes_played(sessions):
    """Sum of minutes across all finished sessions."""
    return sum(
        minutes
        for minutes in (minutes_played(s) for s in sessions)
        if minutes is not None
    )


@st.fragment(run_every=1)
def live_timer(started_at):
    """Count up the time since an active session started, once per second."""
    # The API stores timestamps as naive UTC.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    elapsed = int((now - datetime.fromisoformat(started_at)).total_seconds())
    hours, rest = divmod(max(elapsed, 0), 3600)
    minutes, seconds = divmod(rest, 60)
    st.markdown(
        f"Session Active: ⏱️ **{hours:02d}:{minutes:02d}:{seconds:02d}** elapsed"
    )
