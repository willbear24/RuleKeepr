from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.chunk import SourceChunk


class QuestionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question_text: str = Field(min_length=1, max_length=2000)


class QuestionResponse(BaseModel):
    id: int
    play_session_id: int
    question_text: str
    answer_text: str | None = None
    asked_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuestionAnswerResponse(QuestionResponse):
    """Returned when a question is asked; sources are not stored."""

    sources: list[SourceChunk] = []