from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.limiter import limiter
from backend.app.models.question import Question
from backend.app.models.user import User
from backend.app.routers.sessions import _get_session_or_404
from backend.app.models.game import Game
from backend.app.schemas.question import (
    QuestionAnswerResponse,
    QuestionCreate,
    QuestionResponse,
)
from backend.app.services.rag import answer_question
from backend.app.services.security import get_current_user
from backend.app.utils.exceptions import AppException, NotFoundException

router = APIRouter(
    prefix="/sessions/{session_id}/questions", tags=["Questions"]
)

# Questions are only reachable through a play session the user owns.
# Answers are filled in later by the RAG pipeline; for now answer_text stays empty.


def _get_question_or_404(
    session_id: int, question_id: int, db: Session, current_user: User
) -> Question:
    _get_session_or_404(session_id, db, current_user)
    question = (
        db.query(Question)
        .filter(
            Question.id == question_id,
            Question.play_session_id == session_id,
        )
        .first()
    )
    if question is None:
        raise NotFoundException("Question", question_id)
    return question


# CREATE
@router.post(
    "/",
    response_model=QuestionAnswerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Play session not found."},
        409: {"description": "The play session has already ended."},
        422: {"description": "The question payload failed validation."},
        429: {"description": "Too many requests from this client."},
        503: {"description": "The language model or rulebook search is down; the question is saved without an answer."},
    },
    summary="Ask a question in a play session.",
)
@limiter.limit("20/minute")
def create_question(
    request: Request,
    session_id: int,
    payload: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Store a question for a play session owned by the authenticated user.

    Raises:
        401: No valid Bearer token was provided.
        404: The session does not exist or belongs to another user.
        409: The session has already ended.
        422: The question is empty or too long.
    """
    play_session = _get_session_or_404(session_id, db, current_user)
    if play_session.ended_at is not None:
        raise AppException("Play session has already ended", status_code=409)

    new_question = Question(
        play_session_id=session_id,
        question_text=payload.question_text,
    )
    db.add(new_question)
    db.commit()
    db.refresh(new_question)

    # The question is saved before answering, so a failure here keeps it with no answer.
    game = db.get(Game, play_session.game_id)
    result = answer_question(payload.question_text, game.id, game.title)

    new_question.answer_text = result.answer
    db.commit()
    db.refresh(new_question)
    return QuestionAnswerResponse(
        **QuestionResponse.model_validate(new_question).model_dump(),
        sources=result.sources,
    )


# READ
@router.get(
    "/",
    response_model=list[QuestionResponse],
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Play session not found."},
        429: {"description": "Too many requests from this client."},
    },
    summary="List the questions asked in a play session, oldest first.",
)
@limiter.limit("120/minute")
def list_questions(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a play session's questions in the order they were asked.

    Raises:
        401: No valid Bearer token was provided.
        404: The session does not exist or belongs to another user.
    """
    _get_session_or_404(session_id, db, current_user)
    return (
        db.query(Question)
        .filter(Question.play_session_id == session_id)
        .order_by(Question.asked_at.asc(), Question.id.asc())
        .all()
    )


@router.get(
    "/{question_id}",
    response_model=QuestionResponse,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Play session or question not found."},
        429: {"description": "Too many requests from this client."},
    },
    summary="Retrieve one question.",
)
@limiter.limit("120/minute")
def get_question(
    request: Request,
    session_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve one question from a play session owned by the user.

    Raises:
        401: No valid Bearer token was provided.
        404: The session or question does not exist for this user.
    """
    return _get_question_or_404(session_id, question_id, db, current_user)


# DELETE
@router.delete(
    "/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Play session or question not found."},
        429: {"description": "Too many requests from this client."},
    },
    summary="Delete a question.",
)
@limiter.limit("30/minute")
def delete_question(
    request: Request,
    session_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete one question from a play session owned by the user.

    Raises:
        401: No valid Bearer token was provided.
        404: The session or question does not exist for this user.
    """
    question = _get_question_or_404(session_id, question_id, db, current_user)
    db.delete(question)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
