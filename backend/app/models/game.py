from sqlalchemy import Column, Integer, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.app.database import Base

# Read-only catalog of games, seeded from the rules text files


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=False)
    title = Column(String, nullable=False, unique=True)
    min_player = Column(Integer, nullable=True)
    max_player = Column(Integer, nullable=True)
    play_time_minutes = Column(String, nullable=True)
    rules_filename = Column(String, nullable=False, unique=True)

    user_games = relationship("UserGame", back_populates="game")
