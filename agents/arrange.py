from agents.base import Agent
from langchain_core.language_models.chat_models import BaseChatModel
from lib.prompt import arrange
from lib.skills import with_skills
from models.state import ArrangementOutput, ArrangementPlan, State

class ArrangeAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name = "编曲南郭",
            llm = llm,
            system_prompt=with_skills(arrange(), "arrangement-audio-analysis"),
            output_schema=ArrangementOutput,
            input_fields=(
                "user_request",
                "workflow",
                "creative_brief",
                "lyrics",
                "melody_plan",
                "harmony_plan",
                "rhythm_plan",
                "improvisation_plan",
                "performance_plan",
                "instructions_for_agents",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> ArrangementOutput:
        brief = state.get("creative_brief")
        genre = getattr(brief, "genre", "") if brief else ""
        vocal = getattr(brief, "vocal", False) if brief else False
        production = getattr(brief, "production_style", "") if brief else ""
        workflow = state.get("workflow", "pop_vocal")
        if workflow == "jazz_ensemble":
            instruments = ["次中音萨克斯", "钢琴", "低音提琴", "爵士鼓"]
            texture = "主题采用齐奏或问答，独奏段由节奏组弹性伴奏并逐步增加互动"
        elif workflow == "rock_vocal":
            instruments = ["主唱", "双电吉他", "电贝司", "原声鼓组"]
            texture = "主歌以节奏吉他留出人声空间，副歌展开双轨吉他与完整鼓组"
        elif workflow == "folk_acoustic":
            instruments = ["主唱", "原声吉他", "曼陀林", "低音提琴", "轻打击乐"]
            texture = "以拨弦和叙事人声为中心，乐器用短回应句逐段加入"
        elif workflow == "hiphop_vocal":
            instruments = ["说唱人声", "鼓机", "808 贝斯", "采样切片", "氛围键盘"]
            texture = "verse 保持 beat 与 flow 的留白，hook 加厚人声层和低频重音"
        elif "古典" in genre or "协奏" in state.get("user_request", ""):
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
