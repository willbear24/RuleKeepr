from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlaySessionCreate(BaseModel):
    game_id: int
    notes: str | None = None


class PlaySessionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    notes: str | None = Field(default=None, max_length=2000)


class PlaySessionResponse(BaseModel):
    id: int
    user_id: int
    game_id: int
    started_at: datetime
    ended_at: datetime | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)

