from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.app.database import Base


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    play_session_id = Column(Integer, ForeignKey("play_sessions.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=True)
    asked_at = Column(DateTime, nullable=False, server_default=func.now())

    play_session = relationship("PlaySession", back_populates="questions")