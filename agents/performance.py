from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import performance
from models.state import PerformanceOutput, PerformancePlan, State


class PerformanceAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="Performance Agent",
            llm=llm,
            system_prompt=performance(),
            output_schema=PerformanceOutput,
            input_fields=(
                "user_request",
                "workflow",
                "creative_brief",
                "lyrics",
                "melody_plan",
                "harmony_plan",
                "rhythm_plan",
                "improvisation_plan",
                "instructions_for_agents",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> PerformanceOutput:
        workflow = state.get("workflow", "pop_vocal")
        if workflow == "jazz_ensemble":
            articulation = "旋律略靠后拍，短音有弹性，长音保留气息"
            dynamics = "独奏逐轮升温，合奏重现主题时收紧动态"
            interaction = "节奏组持续聆听独奏，以 comping 和鼓组填充做问答"
            humanization = ["轻微 swing 比例变化", "自然力度起伏", "保留现场呼吸"]
        elif workflow == "rock_vocal":
            articulation = "鼓点坚定，吉他重音利落，人声咬字有推进感"
            dynamics = "主歌克制，预副歌累积，副歌以全乐队动态打开"
            interaction = "贝斯锁定底鼓，双吉他分工节奏墙与回应句"
            humanization = ["鼓组微小力度差", "吉他双轨不完全重合", "保留真实拨弦噪声"]
        elif workflow == "hiphop_vocal":
            articulation = "说唱贴合鼓点重音，在句尾留出 ad-lib 空间"
            dynamics = "verse 以 flow 密度推进，hook 降低字密度并强化重拍"
            interaction = "人声切分与鼓组互补，贝斯在关键词后回应"
            humanization = ["少量抢拍与拖拍", "重音力度层级", "呼吸和 ad-lib 留白"]
        else:
            articulation = "原声乐器触弦自然，人声近讲述感并保留换气"
            dynamics = "从独奏式开场逐步加入合奏，高潮仍保持自然动态"
            interaction = "乐器用短回应句衬托主唱，不覆盖歌词叙事"
            humanization = ["轻微速度浮动", "自然触弦噪声", "段落间保留呼吸"]
        return PerformanceOutput(
            performance_plan=PerformancePlan(
                articulation=articulation,
                dynamics=dynamics,
                ensemble_interaction=interaction,
                humanization=humanization,
            )
        )
