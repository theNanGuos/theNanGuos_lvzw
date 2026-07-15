from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import harmony
from models.state import HarmonyOutput, HarmonyPlan, State


class HarmonyAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="Harmony Agent",
            llm=llm,
            system_prompt=harmony(),
            output_schema=HarmonyOutput,
            input_fields=(
                "user_request",
                "workflow",
                "creative_brief",
                "lyrics",
                "melody_plan",
                "instructions_for_agents",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> HarmonyOutput:
        workflow = state.get("workflow", "pop_vocal")
        if workflow == "classical_instrumental":
            progression = ["I", "vi", "ii", "V", "I"]
            tension = "通过属功能和短暂离调推动主题展开"
        elif workflow == "electronic_instrumental":
            progression = ["i", "VI", "III", "VII"]
            tension = "保持循环和声，靠滤波与层次增加张力"
        else:
            progression = ["I", "V", "vi", "IV"]
            tension = "副歌抬高和声密度并强化 hook 回归"
        return HarmonyOutput(
            harmony_plan=HarmonyPlan(
                key_center="C major / A minor",
                chord_progression=progression,
                harmonic_rhythm="每 1 到 2 小节换和弦",
                tension_strategy=tension,
            )
        )
