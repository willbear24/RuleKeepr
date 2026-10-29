import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from streamlit.testing.v1 import AppTest

from frontend import api_client

FRONTEND = Path(__file__).parent


@pytest.mark.parametrize(
    ("exception", "message"),
    [
        (requests.exceptions.Timeout(), "The RuleKeepr server took too long to respond."),
        (requests.exceptions.ConnectionError(), "Can't reach the RuleKeepr server."),
    ],
)
def test_request_reports_transport_errors(monkeypatch, exception, message):
    monkeypatch.setattr(api_client.requests, "request", Mock(side_effect=exception))

    with pytest.raises(api_client.ApiError, match=message):
        api_client.list_sessions("test-token")


@pytest.mark.parametrize(
    ("status_code", "body", "message"),
    [
        (200, b"<html>not JSON</html>", "The RuleKeepr server returned an invalid response."),
        (502, b"<html>proxy error</html>", "Server error (502)"),
        (503, b'["unexpected error format"]', "Server error (503)"),
        (503, b'{"detail": "Search unavailable"}', "Search unavailable"),
        (422, b'{"detail": [{"msg": "Invalid question"}]}', "[{'msg': 'Invalid question'}]"),
    ],
)
def test_request_handles_invalid_and_error_responses(
    monkeypatch, status_code, body, message
):
    response = requests.Response()
    response.status_code = status_code
    response._content = body
    monkeypatch.setattr(api_client.requests, "request", Mock(return_value=response))

    with pytest.raises(api_client.ApiError) as caught:
        api_client.list_sessions("test-token")

    assert caught.value.message == message
    assert caught.value.status_code == status_code


def test_delete_still_accepts_no_content(monkeypatch):
    response = requests.Response()
    response.status_code = 204
    response._content = b""
    monkeypatch.setattr(api_client.requests, "request", Mock(return_value=response))

    assert api_client.delete_session("test-token", 7) is None


@pytest.fixture
def page_api(monkeypatch):
    monkeypatch.syspath_prepend(str(FRONTEND))
    monkeypatch.setitem(sys.modules, "api_client", api_client)
    monkeypatch.setattr(
        api_client, "my_games",
        lambda _token: [{"game": {"id": 1, "title": "Monopoly"}}],
    )
    monkeypatch.setattr(
        api_client, "list_sessions",
        lambda _token: [{
            "id": 7,
            "game_id": 1,
            "started_at": "2026-10-29T12:00:00",
            "ended_at": None,
        }],
    )
    return api_client


def test_shelf_displays_session_loading_error(page_api, monkeypatch):
    monkeypatch.setattr(
        page_api, "list_sessions",
        Mock(side_effect=api_client.ApiError("Can't load sessions.")),
    )
    page = AppTest.from_file(str(FRONTEND / "pages" / "1_My_Gameshelf.py"))
    page.session_state["token"] = "test-token"

    page.run()

    assert not page.exception
    assert page.error[0].value == "Can't load sessions."


@pytest.mark.parametrize("history_unavailable", [False, True])
def test_failed_question_refreshes_history_without_resubmitting(
    page_api, monkeypatch, history_unavailable
):
    history = Mock(return_value=[])
    monkeypatch.setattr(page_api, "list_questions", history)
    ask = Mock(side_effect=api_client.ApiError("The language model is unavailable", 503))
    monkeypatch.setattr(page_api, "ask_question", ask)
    page = AppTest.from_file(str(FRONTEND / "pages" / "2_Ask_RuleKeepr.py"))
    page.session_state["token"] = "test-token"
    page.run()
    assert not page.exception

    saved_question = {
        "id": 9,
        "question_text": "What happens when I pass Go?",
        "answer_text": None,
        "asked_at": "2026-10-29T12:01:00",
    }
    history.side_effect = [
        [],
        api_client.ApiError("Can't refresh history.") if history_unavailable
        else [saved_question],
    ]
    page.chat_input[0].set_value(saved_question["question_text"]).run()

    assert not page.exception
    assert ask.call_count == 1
    assert history.call_count == 3
    assert page.error[0].value == "The language model is unavailable"
    assert "may already have been saved" in page.warning[0].value
    if history_unavailable:
        assert page.error[1].value == "Can't refresh history."
    else:
        assert page.chat_message[0].markdown[0].value == saved_question["question_text"]
        assert page.chat_message[1].markdown[0].value == "No answer was generated."
