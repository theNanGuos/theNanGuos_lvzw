from agents.base import Agent
from langchain_core.language_models.chat_models import BaseChatModel
from lib.prompt import conductor
from models.state import ConductorOutput

class ConductorAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name = "Conductor Agent",
            llm = llm,
            system_prompt = (
                conductor()
            ),
            output_schema=ConductorOutput,
            input_fields=("user_request", "preset"),
        )
