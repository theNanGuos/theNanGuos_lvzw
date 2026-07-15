from agents.base import Agent
from langchain_core.language_models.chat_models import BaseChatModel
from lib.prompt import melody
from lib.skills import with_skills
from models.state import MelodyOutput, MelodyPlan, State

class MelodyAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name = "Melody Agent",
            llm = llm,
            system_prompt=with_skills(melody(), "melody-demo-audio"),
            output_schema=MelodyOutput,
            input_fields=(
                "user_request",
                "creative_brief",
                "instructions_for_agents",
                "lyrics",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> MelodyOutput:
        brief = state.get("creative_brief")
        tempo_feel = getattr(brief, "tempo_feel", "medium") if brief else "medium"
        tempo = {"slow": "72 BPM", "medium": "96 BPM", "fast": "124 BPM"}.get(
            tempo_feel,
            "96 BPM",
        )
        hook = getattr(state.get("lyrics"), "hook", "") if state.get("lyrics") else ""
        return MelodyOutput(
            melody_plan=MelodyPlan(
                tempo=tempo,
                melody_style="明亮、顺畅、易记的上行旋律线",
                verse_melody="主歌以级进为主，句尾轻微下行留出呼吸",
                chorus_melody="副歌抬高音区，使用重复短句形成记忆点",
                hook=hook or "四小节上行动机",
                harmony="I-V-vi-IV 或相近的大调功能进行",
                rhythm="稳定四拍，弱起进入主旋律",
                emotional_arc="从轻盈铺陈推进到开阔明亮",
            )
        )
