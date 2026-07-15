from agents.base import Agent
from langchain_core.language_models.chat_models import BaseChatModel
from lib.prompt import arrange
from models.state import ArrangementOutput, ArrangementPlan, State

class ArrangeAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name = "Arrange Agent",
            llm = llm,
            system_prompt = (
                arrange()
            ),
            output_schema=ArrangementOutput,
            input_fields=(
                "user_request",
                "creative_brief",
                "lyrics",
                "melody_plan",
                "instructions_for_agents",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> ArrangementOutput:
        brief = state.get("creative_brief")
        genre = getattr(brief, "genre", "") if brief else ""
        vocal = getattr(brief, "vocal", False) if brief else False
        production = getattr(brief, "production_style", "") if brief else ""
        if "古典" in genre or "协奏" in state.get("user_request", ""):
            instruments = ["钢琴", "弦乐组", "低音提琴", "定音鼓"]
            texture = "钢琴主题与弦乐声部交替展开，低音支撑清晰"
        elif vocal:
            instruments = ["鼓组", "电贝司", "原声吉他", "电钢琴", "弦乐铺底"]
            texture = "主歌保持留白，副歌加入完整节奏组和和声铺垫"
        else:
            instruments = ["钢琴", "合成器", "弦乐铺底", "轻打击乐"]
            texture = "旋律在钢琴与合成器之间交替，织体逐段加厚"
        return ArrangementOutput(
            arrangement_plan=ArrangementPlan(
                instrumentation=instruments,
                section_development="intro 建立动机，verse 收束，chorus 扩展主题，outro 保留 hook 余韵",
                texture=texture,
                production=production or "自然、清晰、层次分明",
            )
        )
