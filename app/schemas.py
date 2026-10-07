from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

Text = Annotated[str, Field(min_length=1, max_length=200)]
Slug = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


class ScreenCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Text
    slug: Slug
    location: Text
    active: bool = True


class ScreenUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Text | None = None
    slug: Slug | None = None
    location: Text | None = None
    active: bool | None = None

    @field_validator("name", "slug", "location", "active")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("O campo não pode ser nulo")
        return value


class ScreenRead(ScreenCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def as_utc(cls, value):
        # SQLite armazena datetime sem offset; os valores são sempre UTC.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
