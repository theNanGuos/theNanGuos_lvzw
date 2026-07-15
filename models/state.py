from typing import Literal, TypedDict

from pydantic import BaseModel, Field

WorkflowName = Literal[
    "pop_vocal",
    "classical_instrumental",
    "electronic_instrumental",
    "soundtrack_score",
]


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


class NoteEvent(BaseModel):
    pitch: str | None = None
    duration: float = Field(gt=0, le=16)
    velocity: int = Field(default=72, ge=1, le=127)


class ScorePart(BaseModel):
    name: str
    instrument: str
    notes: list[NoteEvent] = Field(min_length=1, max_length=256)


class ScoreSpec(BaseModel):
    title: str
    tempo_bpm: int = Field(ge=30, le=240)
    time_signature: str = "4/4"
    key_signature: str = "C"
    parts: list[ScorePart] = Field(min_length=1, max_length=16)


class MelodyOutput(BaseModel):
    melody_plan: MelodyPlan
    score_spec: ScoreSpec | None = None


class ArrangementPlan(BaseModel):
    instrumentation: list[str]
    section_development: str
    texture: str
    production: str


class ArrangementOutput(BaseModel):
    arrangement_plan: ArrangementPlan


class HarmonyPlan(BaseModel):
    key_center: str
    chord_progression: list[str] = Field(default_factory=list)
    harmonic_rhythm: str
    tension_strategy: str


class HarmonyOutput(BaseModel):
    harmony_plan: HarmonyPlan


class RhythmPlan(BaseModel):
    groove: str
    percussion: list[str] = Field(default_factory=list)
    rhythmic_motifs: list[str] = Field(default_factory=list)
    energy_curve: str


class RhythmOutput(BaseModel):
    rhythm_plan: RhythmPlan


class SoundDesignPlan(BaseModel):
    palette: list[str] = Field(default_factory=list)
    signature_sounds: list[str] = Field(default_factory=list)
    spatial_motion: str
    texture_notes: str


class SoundDesignOutput(BaseModel):
    sound_design_plan: SoundDesignPlan


class MixReview(BaseModel):
    focus: str
    balance_notes: list[str] = Field(default_factory=list)
    risk_checks: list[str] = Field(default_factory=list)


class MixReviewOutput(BaseModel):
    mix_review: MixReview


class PromptOutput(BaseModel):
    final_prompt: str = Field(min_length=1, max_length=500)


class AudioReference(BaseModel):
    tool: str
    asset_index: int
    result: dict


class State(TypedDict, total=False):
    user_request: str
    preset: Literal[
        "auto",
        "pop_vocal",
        "classical_instrumental",
        "electronic_instrumental",
        "soundtrack_score",
    ]
    reference_audio_paths: list[str]
    audio_references: list[AudioReference]
    workflow: WorkflowName
    creative_brief: CreativeBrief
    instructions_for_agents: dict[str, list[str]]
    lyrics: LyricsDraft
    melody_plan: MelodyPlan
    score_spec: ScoreSpec | None
    harmony_plan: HarmonyPlan
    rhythm_plan: RhythmPlan
    sound_design_plan: SoundDesignPlan
    arrangement_plan: ArrangementPlan
    mix_review: MixReview
    score_artifacts: dict[str, str]
    artifact_dir: str
    final_prompt: str
