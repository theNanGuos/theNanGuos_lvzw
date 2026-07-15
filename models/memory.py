from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from models.project import ProjectPreset, utc_now

MemoryKind = Literal["preference", "avoidance", "habit"]


class MemoryObservation(BaseModel):
    kind: MemoryKind
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=300)
    confidence: float = Field(default=0.6, ge=0, le=1)
    evidence: str = Field(default="", max_length=500)


class UserPreference(BaseModel):
    kind: MemoryKind
    key: str
    value: str
    confidence: float = Field(ge=0, le=1)
    evidence_count: int = Field(default=1, ge=1)
    source_session_ids: list[str] = Field(default_factory=list)
    last_seen_at: datetime = Field(default_factory=utc_now)


class UserProfile(BaseModel):
    preferences: list[UserPreference] = Field(default_factory=list)
    workflow_counts: dict[ProjectPreset, int] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=utc_now)


class PortfolioTrack(BaseModel):
    title: str
    audio_url: str
    download_url: str
    cover_url: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    style: str = ""


class PortfolioItem(BaseModel):
    project_id: str
    title: str
    user_request: str
    preset: ProjectPreset
    status: str
    progress: int = Field(ge=0, le=100)
    current_stage: str
    latest_run_id: str | None = None
    tracks: list[PortfolioTrack] = Field(default_factory=list)
    updated_at: datetime


class MemoryContext(BaseModel):
    preferences: list[UserPreference] = Field(default_factory=list)
    workflow_counts: dict[ProjectPreset, int] = Field(default_factory=dict)
    previous_works: list[PortfolioItem] = Field(default_factory=list)
