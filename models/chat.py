from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

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


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    role: ChatRole
    content: str = Field(min_length=1, max_length=4000)
    created_at: datetime = Field(default_factory=utc_now)


class ChatSession(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str = Field(default="新会话", max_length=100)
    messages: list[ChatMessage] = Field(default_factory=list)
    summary: str = Field(default="", max_length=4000)
    active_project_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatSessionCreate(BaseModel):
    title: str = Field(default="新会话", min_length=1, max_length=100)


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
