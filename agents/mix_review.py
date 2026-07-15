from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import mix_review
from models.state import MixReviewOutput, MixReview, State


class MixReviewAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="Mix Review Agent",
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
        else:
            risks = ["高潮不要过早释放", "空间感不要掩盖主题动机"]
        return MixReviewOutput(
            mix_review=MixReview(
                focus=focus,
                balance_notes=["低频稳定", "主旋律靠前", "空间效果服务段落"],
                risk_checks=risks,
            )
        )
