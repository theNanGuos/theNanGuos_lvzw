from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import improvisation
from models.state import ImprovisationOutput, ImprovisationPlan, State


class ImprovisationAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="即兴南郭",
            llm=llm,
            system_prompt=improvisation(),
            output_schema=ImprovisationOutput,
            input_fields=(
                "user_request",
                "creative_brief",
                "melody_plan",
                "harmony_plan",
                "rhythm_plan",
                "instructions_for_agents",
            ),
        )

    def fallback(self, state: State, exc: Exception) -> ImprovisationOutput:
        return ImprovisationOutput(
            improvisation_plan=ImprovisationPlan(
                soloists=["次中音萨克斯", "钢琴"],
                solo_form="主题后各一轮短独奏，末段四小节交替后回到主题",
                vocabulary=["和弦音导向", "经过音", "动机发展", "节奏位移"],
                ensemble_interaction="鼓与贝斯保持弹性脉冲，钢琴用稀疏 comping 回应独奏句",
                guardrails=["每轮保留主题动机", "避免持续高密度炫技", "清楚提示回到主旋律"],
            )
        )
