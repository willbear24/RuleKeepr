from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Jane Doe",
                "email": "jane@example.com",
                "is_active": True,
                "created_at": "2026-10-22T11:38:00",
            }
        },
    )


class UserUpdate(BaseModel):
    """Input schema for partially updating the current user's information."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="The user's name",
        examples=["Jane Doe"],
    )
    email: EmailStr | None = Field(
        default=None,
        description="A new email address; requires current_password",
        examples=["jane@example.com"],
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        description="A new password; requires current_password",
    )
    current_password: str | None = Field(
        default=None,
        description="Required when changing email or password",
    )

    @model_validator(mode="after")
    def validate_update(self) -> "UserUpdate":
        for field in ("name", "email", "password"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        if (self.email is not None or self.password is not None) and not self.current_password:
            raise ValueError("current_password is required to change email or password")
        return self
