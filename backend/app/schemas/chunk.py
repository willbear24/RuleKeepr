from pydantic import BaseModel, Field
from typing import Optional
from pydantic.config import ConfigDict


class SourceChunk(BaseModel):
    game_id: int
    game_title: str
    chunk_index: int
    section: str | None = None
    text: str
    score: float | None = None

    model_config = ConfigDict(from_attributes=True)
