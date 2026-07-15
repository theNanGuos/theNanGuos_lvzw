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
                "creative_brief",
                "lyrics",
                "melody_plan",
                "arrangement_plan",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> PromptOutput:
        brief = state.get("creative_brief")
        melody = state.get("melody_plan")
        arrangement = state.get("arrangement_plan")
        lyrics = state.get("lyrics")
        parts = [
            getattr(brief, "genre", "") if brief else "",
            "、".join(getattr(brief, "mood", []) or []) if brief else "",
            getattr(brief, "production_style", "") if brief else "",
            getattr(melody, "tempo", "") if melody else "",
            getattr(melody, "melody_style", "") if melody else "",
            "、".join(getattr(arrangement, "instrumentation", []) or []) if arrangement else "",
            getattr(arrangement, "production", "") if arrangement else "",
        ]
        if lyrics:
            parts.append(f"hook: {lyrics.hook}")
        if brief and not getattr(brief, "vocal", False):
            parts.append("instrumental, no vocals")
        prompt = "，".join(part for part in parts if part)
        return PromptOutput(final_prompt=prompt[:500] or state.get("user_request", "生成一首完整音乐作品"))
