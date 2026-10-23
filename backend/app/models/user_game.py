from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.app.database import Base


class UserGame(Base):
    __tablename__ = "user_games"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), primary_key=True)
    notes = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    added_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="user_games")
    game = relationship("Game", back_populates="user_games")
    play_sessions = relationship(
        "PlaySession",
        back_populates="user_game",
        cascade="all, delete-orphan",
    )
