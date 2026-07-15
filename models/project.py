from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ProjectStatus = Literal["draft", "running", "completed", "failed"]
ProjectPreset = Literal[
    "auto",
    "pop_vocal",
    "classical_instrumental",
    "electronic_instrumental",
    "soundtrack_score",
]


def utc_now() -> datetime:
    return datetime.now(UTC)


class Asset(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    filename: str
    path: str
    content_type: str
    size: int


class Project(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    user_request: str
    preset: ProjectPreset = "auto"
    status: ProjectStatus = "draft"
    assets: list[Asset] = Field(default_factory=list)
    latest_run_id: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    user_request: str = Field(min_length=1, max_length=2000)
    preset: ProjectPreset = "auto"


class RunResult(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    project_id: str
    state: dict[str, Any]
    created_at: datetime = Field(default_factory=utc_now)
