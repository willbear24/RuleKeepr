from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.limiter import limiter
from backend.app.models.play_session import PlaySession
from backend.app.models.user import User
from backend.app.models.user_game import UserGame
from backend.app.schemas.play_session import (
    PlaySessionCreate,
    PlaySessionResponse,
    PlaySessionUpdate,
)
from backend.app.services.security import get_current_user
from backend.app.utils.exceptions import AppException, NotFoundException

router = APIRouter(prefix="/sessions", tags=["Play Sessions"])


def _get_session_or_404(
    session_id: int, db: Session, current_user: User
) -> PlaySession:
    session = (
        db.query(PlaySession)
        .filter(
            PlaySession.id == session_id,
            PlaySession.user_id == current_user.id,
        )
        .first()
    )
    if session is None:
        raise NotFoundException("Play session", session_id)
    return session


# CREATE
@router.post(
    "/",
    response_model=PlaySessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The game is not on your shelf."},
        422: {"description": "The play session payload failed validation."},
        429: {"description": "Too many requests from this client."},
    },
    summary="Create a new play session.",
)
@limiter.limit("10/minute")
def create_play_session(
    request: Request,
    payload: PlaySessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a play session for a game on the user's shelf."""
    on_shelf = (
        db.query(UserGame)
        .filter(
            UserGame.user_id == current_user.id,
            UserGame.game_id == payload.game_id,
        )
        .first()
    )
    if on_shelf is None:
        raise NotFoundException("Shelf entry for game", payload.game_id)

    new_session = PlaySession(
        user_id=current_user.id,
        game_id=payload.game_id,
        notes=payload.notes,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


# End a playsession
@router.post(
    "/{session_id}/end",
    response_model=PlaySessionResponse,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The play session was not found."},
        409: {"description": "The play session has already ended."},
        429: {"description": "Too many requests from this client."},
    },
    summary="End a play session.",
)
@limiter.limit("10/minute")
def end_play_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a play session as ended. The server sets the end time."""
    play_session = _get_session_or_404(session_id, db, current_user)
    if play_session.ended_at is not None:
        raise AppException("Play session has already ended", status_code=409)

    # started_at uses the database's UTC clock, so store a naive UTC time too.
    play_session.ended_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(play_session)
    return play_session


# READ
@router.get(
    "/",
    response_model=list[PlaySessionResponse],
    responses={
        401: {"description": "Authentication is required."},
        429: {"description": "Too many requests from this client."},
    },
    summary="List the current user's play sessions, newest first.",
)
@limiter.limit(
    "120/minute"
)  # Prevents an absurd payload pull, should't be a problem anyway unless heavy server traffic
def list_sessions(
    request: Request,
    game_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's play sessions, newest first.

    Pass game_id to only see sessions for one game.

    Raises:
        401: No valid Bearer token was provided.
    """
    query = db.query(PlaySession).filter(PlaySession.user_id == current_user.id)
    if game_id is not None:
        query = query.filter(PlaySession.game_id == game_id)

    return query.order_by(PlaySession.started_at.desc(), PlaySession.id.desc()).all()


@router.get(
    "/{session_id}",
    response_model=PlaySessionResponse,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Play session not found."},
        429: {"description": "Too many requests from this client."},
    },
    summary="Retrieve one play session.",
)
@limiter.limit("120/minute")
def get_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve one play session owned by the authenticated user.

    Raises:
        401: No valid Bearer token.
        404: The session does not exist or belongs to another user.
    """
    return _get_session_or_404(session_id, db, current_user)


# UPDATE
@router.patch(
    "/{session_id}",
    response_model=PlaySessionResponse,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Play session not found."},
        422: {"description": "The play session payload failed validation."},
        429: {"description": "Too many requests from this client."},
    },
    summary="Update a play session's notes.",
)
@limiter.limit("30/minute")
def update_session(
    request: Request,
    session_id: int,
    payload: PlaySessionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the notes on a play session owned by the authenticated user.

    Raises:
        401: No valid Bearer token was provided.
        404: The session does not exist or belongs to another user.
        422: The payload contains unknown or invalid fields.
    """
    play_session = _get_session_or_404(session_id, db, current_user)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(play_session, field, value)

    db.commit()
    db.refresh(play_session)
    return play_session


# DELETE
@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "Play session not found."},
        429: {"description": "Too many requests from this client."},
    },
    summary="Delete a play session and its questions.",
)
@limiter.limit("30/minute")
def delete_session(
    request: Request,
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a play session owned by the authenticated user.

    The session's questions are deleted with it.

    Raises:
        401: No valid Bearer token was provided.
        404: The session does not exist or belongs to another user.
    """
    play_session = _get_session_or_404(session_id, db, current_user)
    db.delete(play_session)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
