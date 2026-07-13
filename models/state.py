from typing import Literal, TypedDict

from pydantic import BaseModel, Field

WorkflowName = Literal["pop_vocal", "classical_instrumental"]


class CreativeBrief(BaseModel):
    title: str
    language: str = "instrumental"
    genre: str
    mood: list[str] = Field(default_factory=list)
    theme: str
    duration_seconds: int = Field(default=90, ge=30, le=600)
    tempo_feel: Literal["slow", "medium", "fast"] = "medium"
    vocal: bool
    vocal_style: str = ""
    song_structure: list[str] = Field(default_factory=list)
    production_style: str


class ConductorOutput(BaseModel):
    workflow: WorkflowName
    creative_brief: CreativeBrief
    instructions_for_agents: dict[str, list[str]] = Field(default_factory=dict)


class LyricsDraft(BaseModel):
    intro: list[str] = Field(default_factory=list)
    verse: list[str] = Field(default_factory=list)
    chorus: list[str] = Field(default_factory=list)
    outro: list[str] = Field(default_factory=list)
    language: str
    theme: str
    hook: str
    singing_style_hint: str


class LyricsOutput(BaseModel):
    lyrics: LyricsDraft


class MelodyPlan(BaseModel):
    tempo: str
    melody_style: str
    verse_melody: str = ""
    chorus_melody: str = ""
    hook: str = ""
    harmony: str
    rhythm: str
    emotional_arc: str


class MelodyOutput(BaseModel):
    melody_plan: MelodyPlan


class ArrangementPlan(BaseModel):
    instrumentation: list[str]
    section_development: str
    texture: str
    production: str


class ArrangementOutput(BaseModel):
    arrangement_plan: ArrangementPlan


class PromptOutput(BaseModel):
    final_prompt: str = Field(min_length=1, max_length=500)


class State(TypedDict, total=False):
    user_request: str
    workflow: WorkflowName
    creative_brief: CreativeBrief
    instructions_for_agents: dict[str, list[str]]
    lyrics: LyricsDraft
    melody_plan: MelodyPlan
    arrangement_plan: ArrangementPlan
    final_prompt: str
