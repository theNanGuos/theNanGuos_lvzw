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
    "jazz_ensemble",
    "rock_vocal",
    "folk_acoustic",
    "hiphop_vocal",
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
    genre: str = Field(default="auto", max_length=80)
    language: str = Field(default="auto", max_length=40)
    instruments: list[str] = Field(default_factory=list, max_length=12)
    status: ProjectStatus = "draft"
    progress: int = Field(default=0, ge=0, le=100)
    current_stage: str = "draft"
    workflow: str | None = None
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    assets: list[Asset] = Field(default_factory=list)
    latest_run_id: str | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    user_request: str = Field(min_length=1, max_length=2000)
    preset: ProjectPreset = "auto"
    genre: str = Field(default="auto", max_length=80)
    language: str = Field(default="auto", max_length=40)
    instruments: list[str] = Field(default_factory=list, max_length=12)


class RunResult(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    project_id: str
    state: dict[str, Any] = Field(default_factory=dict)
    status: ProjectStatus = "completed"
    progress: int = Field(default=100, ge=0, le=100)
    current_stage: str = "completed"
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
