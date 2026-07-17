from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import rhythm
from models.state import RhythmOutput, RhythmPlan, State


class RhythmAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="节奏南郭",
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
        elif workflow == "jazz_ensemble":
            groove = "弹性的 swing ride pattern，二四拍 hi-hat，walking bass 推进"
            percussion = ["ride cymbal", "hi-hat", "snare comping", "walking bass"]
        elif workflow == "rock_vocal":
            groove = "鼓贝锁定的八分音符推进，副歌开放镲片强化冲击"
            percussion = ["原声鼓组", "电贝司", "节奏吉他闷音"]
        elif workflow == "hiphop_vocal":
            groove = "kick 与 snare 留出说唱切分空间，hi-hat 用局部滚奏推进"
            percussion = ["kick", "snare", "hi-hat", "808 bass"]
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
