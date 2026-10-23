from sqlalchemy import Column, DateTime, ForeignKeyConstraint, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.app.database import Base


class PlaySession(Base):
    __tablename__ = "play_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    game_id = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "game_id"],
            ["user_games.user_id", "user_games.game_id"],
        ),
    )

    user_game = relationship("UserGame", back_populates="play_sessions")
    questions = relationship(
        "Question",
        back_populates="play_session",
        cascade="all, delete-orphan",
    )