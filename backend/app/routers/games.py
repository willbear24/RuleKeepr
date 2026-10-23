from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.limiter import limiter
from backend.app.models.game import Game
from backend.app.models.user import User
from backend.app.models.user_game import UserGame
from backend.app.schemas.game import (
    GameResponse,
    ShelfEntryCreate,
    ShelfEntryResponse,
)
from backend.app.services.security import get_current_user
from backend.app.utils.exceptions import DuplicateException, NotFoundException

router = APIRouter(prefix="/games", tags=["Games"])

# Games are a read-only catalog seeded from the rules text files.
# Users add catalog games to their own shelf (a UserGame row).


def _get_game_or_404(game_id: int, db: Session) -> Game:
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise NotFoundException("Game", game_id)
    return game


def _get_shelf_entry_or_404(
    game_id: int, db: Session, current_user: User
) -> UserGame:
    _get_game_or_404(game_id, db)
    entry = (
        db.query(UserGame)
        .filter(UserGame.game_id == game_id, UserGame.user_id == current_user.id)
        .first()
    )
    if entry is None:
        raise NotFoundException("Shelf entry for game", game_id)
    return entry


# READ


@router.get(
    "/",
    response_model=list[GameResponse],
    responses={
        401: {"description": "Authentication is required."},
        429: {"description": "Too many requests from this client."},
    },
    summary="List every game in the catalog.",
)
@limiter.limit("60/minute")
def list_games(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Game]:
    return db.query(Game).order_by(Game.title).all()


# Declared before "/{game_id}" so "mine" is not parsed as a game id.
@router.get(
    "/mine",
    response_model=list[ShelfEntryResponse],
    responses={
        401: {"description": "Authentication is required."},
        429: {"description": "Too many requests from this client."},
    },
    summary="List the games on the current user's shelf.",
)
@limiter.limit("60/minute")
def list_my_games(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserGame]:
    return (
        db.query(UserGame)
        .join(Game, Game.id == UserGame.game_id)
        .filter(UserGame.user_id == current_user.id)
        .order_by(Game.title)
        .all()
    )


@router.get(
    "/{game_id}",
    response_model=GameResponse,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The game does not exist."},
        429: {"description": "Too many requests from this client."},
    },
    summary="Get a game from the catalog.",
)
@limiter.limit("60/minute")
def get_game(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Game:
    return _get_game_or_404(game_id, db)


# SHELF: add / remove a catalog game for the current user


@router.post(
    "/{game_id}/shelf",
    response_model=ShelfEntryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The game does not exist."},
        409: {"description": "The game is already on the user's shelf."},
        422: {"description": "The payload failed validation."},
        429: {"description": "Too many requests from this client."},
    },
    summary="Add a catalog game to the current user's shelf.",
)
@limiter.limit("30/minute")
def add_game_to_shelf(
    request: Request,
    game_id: int,
    details: ShelfEntryCreate | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserGame:
    game = _get_game_or_404(game_id, db)

    existing = (
        db.query(UserGame)
        .filter(UserGame.game_id == game_id, UserGame.user_id == current_user.id)
        .first()
    )
    if existing:
        raise DuplicateException("Shelf entry", "game", game.title)

    details = details or ShelfEntryCreate()
    entry = UserGame(
        user_id=current_user.id,
        game_id=game_id,
        notes=details.notes,
        rating=details.rating,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete(
    "/{game_id}/shelf",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        401: {"description": "Authentication is required."},
        404: {"description": "The game does not exist or is not on the shelf."},
        429: {"description": "Too many requests from this client."},
    },
    summary="Remove a game from the current user's shelf.",
)
@limiter.limit("30/minute")
def remove_game_from_shelf(
    request: Request,
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Remove the shelf entry and this user's play sessions for the game.

    The catalog game and other users' shelves are not affected.
    """
    entry = _get_shelf_entry_or_404(game_id, db, current_user)
    db.delete(entry)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
