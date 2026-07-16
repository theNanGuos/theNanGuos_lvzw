from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import prompt_compiler
from lib.skills import with_skills
from models.state import State, PromptOutput


class PromptCompilerAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="Prompt Compiler Agent",
            llm=llm,
            system_prompt=with_skills(prompt_compiler(), "suno-prompt-tool-handoff"),
            output_schema=PromptOutput,
            input_fields=(
                "user_request",
                "memory_context",
                "effective_preferences",
                "creative_brief",
                "lyrics",
                "melody_plan",
                "harmony_plan",
                "rhythm_plan",
                "sound_design_plan",
                "arrangement_plan",
                "mix_review",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> PromptOutput:
        brief = state.get("creative_brief")
        melody = state.get("melody_plan")
        harmony = state.get("harmony_plan")
        rhythm = state.get("rhythm_plan")
        sound_design = state.get("sound_design_plan")
        arrangement = state.get("arrangement_plan")
        mix_review = state.get("mix_review")
        lyrics = state.get("lyrics")
        parts = [
            getattr(brief, "genre", "") if brief else "",
            "、".join(getattr(brief, "mood", []) or []) if brief else "",
            getattr(brief, "production_style", "") if brief else "",
            getattr(melody, "tempo", "") if melody else "",
            getattr(melody, "melody_style", "") if melody else "",
            "、".join(getattr(harmony, "chord_progression", []) or []) if harmony else "",
            getattr(rhythm, "groove", "") if rhythm else "",
            "、".join(getattr(sound_design, "palette", []) or []) if sound_design else "",
            "、".join(getattr(arrangement, "instrumentation", []) or []) if arrangement else "",
            getattr(arrangement, "production", "") if arrangement else "",
            getattr(mix_review, "focus", "") if mix_review else "",
        ]
        if lyrics:
            parts.append(f"hook: {lyrics.hook}")
        if brief and not getattr(brief, "vocal", False):
            parts.append("instrumental, no vocals")
        prompt = "，".join(part for part in parts if part)
        return PromptOutput(final_prompt=prompt[:500] or state.get("user_request", "生成一首完整音乐作品"))
