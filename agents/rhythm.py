from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import rhythm
from models.state import RhythmOutput, RhythmPlan, State


class RhythmAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="Rhythm Agent",
            llm=llm,
            system_prompt=rhythm(),
            output_schema=RhythmOutput,
            input_fields=(
                "user_request",
                "workflow",
                "creative_brief",
                "lyrics",
                "melody_plan",
                "harmony_plan",
                "instructions_for_agents",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> RhythmOutput:
        workflow = state.get("workflow", "pop_vocal")
        if workflow == "electronic_instrumental":
            groove = "四拍底鼓、切分 hi-hat、弹跳合成贝司"
            percussion = ["kick", "snare/clap", "hi-hat", "sub bass pulse"]
        elif workflow == "classical_instrumental":
            groove = "低音型与弦乐分解节奏推动"
            percussion = ["低音弦乐", "定音鼓点缀"]
        else:
            groove = "稳定四拍，主歌留白，副歌全鼓组推进"
            percussion = ["鼓组", "拍手", "轻打击乐"]
        return RhythmOutput(
            rhythm_plan=RhythmPlan(
                groove=groove,
                percussion=percussion,
                rhythmic_motifs=["弱起进入", "副歌切分强调"],
                energy_curve="intro 克制，主歌铺垫，副歌增强，桥段回落后再爆发",
            )
        )
