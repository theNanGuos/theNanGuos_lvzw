from agents.base import Agent
from langchain_core.language_models.chat_models import BaseChatModel
from lib.prompt import conductor
from lib.skills import with_skills
from models.state import ConductorOutput

class ConductorAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name = "指挥南郭",
            llm = llm,
            system_prompt=with_skills(conductor(), "conductor-tool-routing"),
            output_schema=ConductorOutput,
            input_fields=("user_request", "preset", "memory_context", "effective_preferences"),
        )
