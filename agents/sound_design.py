from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import sound_design
from models.state import SoundDesignOutput, SoundDesignPlan, State


class SoundDesignAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="音色南郭",
            llm=llm,
            system_prompt=sound_design(),
            output_schema=SoundDesignOutput,
            input_fields=(
                "user_request",
                "workflow",
                "creative_brief",
                "melody_plan",
                "harmony_plan",
                "rhythm_plan",
                "improvisation_plan",
                "performance_plan",
                "arrangement_plan",
                "instructions_for_agents",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> SoundDesignOutput:
        workflow = state.get("workflow", "pop_vocal")
        if workflow == "electronic_instrumental":
            palette = ["warm pad", "pluck synth", "sub bass", "sidechain ambience"]
            signature = ["filtered riser", "granular vocal chop texture"]
        elif workflow == "soundtrack_score":
            palette = ["弦乐长音", "低频氛围", "远景铜管", "空间打击"]
            signature = ["反向氛围吸入", "宽混响尾音"]
        elif workflow == "jazz_ensemble":
            palette = ["温暖铜管", "木质低音提琴", "自然爵士鼓", "近距离钢琴"]
            signature = ["现场房间反射", "独奏呼吸与按键细节"]
        elif workflow == "rock_vocal":
            palette = ["过载节奏吉他", "有冲击力的原声鼓", "结实电贝司", "贴前人声"]
            signature = ["反馈尾音", "副歌吉他双轨展开"]
        elif workflow == "folk_acoustic":
            palette = ["原声木吉他", "贴近人声", "木质低频", "轻柔房间声"]
            signature = ["拨弦与换把细节", "自然换气"]
        elif workflow == "hiphop_vocal":
            palette = ["有力 kick", "干脆 snare", "808 sub", "采样纹理"]
            signature = ["vocal chop 点缀", "段落切换 drop"]
        else:
            palette = ["自然空间", "柔和 pad", "细节打击"]
            signature = ["段落转场 swell"]
        return SoundDesignOutput(
            sound_design_plan=SoundDesignPlan(
                palette=palette,
                signature_sounds=signature,
                spatial_motion="副歌或高潮处拓宽声场，段落过渡使用自动化推进",
                texture_notes="保持主旋律清晰，避免音色堆叠遮挡 hook",
            )
        )
