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
        elif workflow == "jazz_ensemble":
            progression = ["ii7", "V7", "Imaj7", "VI7", "ii7", "V7"]
            tension = "用导音、替代属和弦与短暂转调连接主题和独奏段"
        elif workflow == "folk_acoustic":
            progression = ["I", "IV", "I", "V", "vi", "IV"]
            tension = "保持开放和弦色彩，在叙事转折处短暂加入次属和弦"
        elif workflow == "hiphop_vocal":
            progression = ["i7", "VImaj7"]
            tension = "保持和声循环稳定，以音色变化和低音经过音推动段落"
        elif workflow == "rock_vocal":
            progression = ["I", "bVII", "IV", "I"]
            tension = "预副歌增加属功能或持续低音，副歌回到强有力的主和弦"
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
