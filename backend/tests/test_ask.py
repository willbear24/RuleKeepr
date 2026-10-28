import pytest

from backend.app.routers import questions as questions_router
from backend.app.schemas.chunk import SourceChunk
from backend.app.services.rag import RagAnswer


@pytest.fixture
def active_session(client, sample_game, auth_headers):
    game_id = sample_game["id"]
    shelf_response = client.post(
        f"/games/{game_id}/shelf",
        headers=auth_headers,
    )
    assert shelf_response.status_code == 201

    session_response = client.post(
        "/sessions/",
        headers=auth_headers,
        json={"game_id": game_id},
    )
    assert session_response.status_code == 201
    return session_response.json()["id"]


class TestAskQuestion:
    def test_ask_question_returns_answer_and_sources(
        self, client, sample_game, active_session, auth_headers, monkeypatch
    ):
        game_id = sample_game["id"]
        session_id = active_session
        expected_answer = "Collect 200 when you pass Go."
        expected_source = SourceChunk(
            game_id=game_id,
            game_title=sample_game["title"],
            chunk_index=0,
            section="PASSING GO",
            text="Each time a player's token passes over or lands on GO, the Banker pays them $200.",
            score=0.92,
        )
        # Temporary function to replace the real answer_question function with for test purposes
        def fake_answer_question(question, requested_game_id, game_title):
            assert question == "What happens when I pass Go?"
            assert requested_game_id == game_id
            assert game_title == sample_game["title"]
            return RagAnswer(
                answer=expected_answer,
                sources=[expected_source],
            )

        monkeypatch.setattr(
            questions_router, "answer_question", fake_answer_question
        )

        response = client.post(
            f"/sessions/{session_id}/questions/",
            headers=auth_headers,
            json={"question_text": "What happens when I pass Go?"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["play_session_id"] == session_id
        assert body["question_text"] == "What happens when I pass Go?"
        assert body["answer_text"] == expected_answer
        assert body["sources"] == [expected_source.model_dump()]

    def test_blank_question_is_rejected(self, client, active_session, auth_headers):
        response = client.post(
            f"/sessions/{active_session}/questions/",
            headers=auth_headers,
            json={"question_text": "   "},
        )

        assert response.status_code == 422
        assert response.json()["detail"][0]["type"] == "string_too_short"
        assert response.json()["detail"][0]["loc"] == ["body", "question_text"]

    def test_question_over_max_length_is_rejected(
        self, client, active_session, auth_headers
    ):
        response = client.post(
            f"/sessions/{active_session}/questions/",
            headers=auth_headers,
            json={"question_text": "q" * 2001},
        )

        assert response.status_code == 422
        assert response.json()["detail"][0]["type"] == "string_too_long"
        assert response.json()["detail"][0]["loc"] == ["body", "question_text"]

    def test_irrelevant_question_returns_not_covered_answer(
        self, client, active_session, auth_headers, monkeypatch
    ):
        monkeypatch.setattr(
            "backend.app.services.rag.retrieve",
            lambda *_args, **_kwargs: [],
        )

        response = client.post(
            f"/sessions/{active_session}/questions/",
            headers=auth_headers,
            json={"question_text": "What is the capital of France?"},
        )

        assert response.status_code == 201
        assert response.json()["answer_text"] == (
            "I couldn't find anything in the rulebook that answers that."
        )
        assert response.json()["sources"] == []
