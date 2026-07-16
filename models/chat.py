from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from models.memory import MemoryObservation
from models.project import ProjectPreset, utc_now

ChatRole = Literal["user", "assistant"]
ChatAction = Literal[
    "chat_only",
    "create_project",
    "run_workflow",
    "revise_project",
    "list_portfolio",
    "ask_clarification",
]


class ChatWorkflowRun(BaseModel):
    project_id: str
    run_id: str
    title: str
    preset: ProjectPreset


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    role: ChatRole
    content: str = Field(min_length=1, max_length=4000)
    workflow_run: ChatWorkflowRun | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str = Field(default="新会话", max_length=100)
    messages: list[ChatMessage] = Field(default_factory=list)
    summary: str = Field(default="", max_length=4000)
    active_project_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    active_project_id: str | None = None
    message_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class ChatSessionCreate(BaseModel):
    title: str = Field(default="新会话", min_length=1, max_length=100)


class ChatSessionUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=100)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("Session title cannot be blank")
        return title


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ChatDecision(BaseModel):
    reply: str = Field(min_length=1, max_length=2000)
    action: ChatAction = "chat_only"
    preset: ProjectPreset = "auto"
    project_title: str = Field(default="", max_length=100)
    user_request: str = Field(default="", max_length=2000)
    memory_observations: list[MemoryObservation] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session: ChatSession
    message: ChatMessage
    action: ChatAction
    project_id: str | None = None
    run_id: str | None = None
