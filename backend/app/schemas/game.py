from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GameResponse(BaseModel):
    id: int
    title: str
    min_player: int | None = None
    max_player: int | None = None
    play_time_minutes: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Settlers of Catan",
                "min_player": 3,
                "max_player": 4,
                "play_time_minutes": "45-60",
            }
        },
    )


class ShelfEntryCreate(BaseModel):
    """Optional details when adding a game to the current user's shelf."""

    model_config = ConfigDict(str_strip_whitespace=True)

    notes: str | None = Field(default=None, max_length=2000)
    rating: int | None = Field(default=None, ge=1, le=5)


class ShelfEntryResponse(BaseModel):
    game: GameResponse
    notes: str | None = None
    rating: int | None = None
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)
