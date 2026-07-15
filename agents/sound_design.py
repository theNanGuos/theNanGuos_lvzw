from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import sound_design
from models.state import SoundDesignOutput, SoundDesignPlan, State


class SoundDesignAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="Sound Design Agent",
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
