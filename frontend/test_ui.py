import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from frontend import api_client
from frontend.ui import format_play_time


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (0, "0 min"),
        (1, "1 min"),
        (59, "59 min"),
        (60, "1.0 hr"),
        (61, "1.0 hr"),
        (90, "1.5 hr"),
        (720, "12.0 hr"),
        (1440, "24.0 hr"),
        (60000, "1,000.0 hr"),
    ],
)
def test_format_play_time(minutes, expected):
    assert format_play_time(minutes) == expected


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(59, "59 min"), (60, "1.0 hr"), (90, "1.5 hr"), (720, "12.0 hr")],
)
def test_dashboard_formats_time_played(monkeypatch, minutes, expected):
    frontend = Path(__file__).parent
    monkeypatch.syspath_prepend(str(frontend))
    monkeypatch.setitem(sys.modules, "api_client", api_client)
    monkeypatch.setattr(api_client, "my_games", lambda _token: [])
    monkeypatch.setattr(api_client, "list_games", lambda _token: [])
    started = datetime(2026, 10, 29, 12)
    monkeypatch.setattr(
        api_client,
        "list_sessions",
        lambda _token: [{
            "game_id": 1,
            "started_at": started.isoformat(),
            "ended_at": (started + timedelta(minutes=minutes)).isoformat(),
        }],
    )
    page = AppTest.from_file(str(frontend / "Home.py"))
    page.session_state["token"] = "test-token"
    page.session_state["user"] = {"name": "Player", "email": "player@example.com"}

    page.run()

    assert not page.exception
    metric = next(metric for metric in page.metric if metric.label == "Time played")
    assert metric.value == expected
