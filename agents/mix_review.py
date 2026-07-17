from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import mix_review
from models.state import MixReviewOutput, MixReview, State


class MixReviewAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="审听南郭",
            llm=llm,
            system_prompt=mix_review(),
            output_schema=MixReviewOutput,
            input_fields=(
                "workflow",
                "creative_brief",
                "lyrics",
                "melody_plan",
                "harmony_plan",
                "rhythm_plan",
                "improvisation_plan",
                "performance_plan",
                "sound_design_plan",
                "arrangement_plan",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> MixReviewOutput:
        workflow = state.get("workflow", "pop_vocal")
        focus = "保持主题清晰并让最终提示词聚焦"
        if workflow == "pop_vocal":
            risks = ["人声不要被配器遮挡", "hook 必须短而清楚"]
        elif workflow == "electronic_instrumental":
            risks = ["低频与底鼓不要拥挤", "音色变化要有段落推进"]
        elif workflow == "jazz_ensemble":
            risks = ["独奏不要脱离主题与曲式", "保留节奏组动态和现场互动"]
        elif workflow == "rock_vocal":
            risks = ["吉他墙不要遮挡主唱", "鼓贝冲击力不能以过度压缩换取"]
        elif workflow == "folk_acoustic":
            risks = ["保留原声动态与触弦细节", "伴奏回应不要干扰歌词叙事"]
        elif workflow == "hiphop_vocal":
            risks = ["808 与 kick 避免低频冲突", "flow、hook 和 ad-lib 保持层级"]
        else:
            risks = ["高潮不要过早释放", "空间感不要掩盖主题动机"]
        return MixReviewOutput(
            mix_review=MixReview(
                focus=focus,
                balance_notes=["低频稳定", "主旋律靠前", "空间效果服务段落"],
                risk_checks=risks,
            )
        )
