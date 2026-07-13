from agents.base import Agent
from langchain_core.language_models.chat_models import BaseChatModel
from lib.prompt import melody
from models.state import MelodyOutput

class MelodyAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name = "Melody Agent",
            llm = llm,
            system_prompt = (
                melody()
            ),
            output_schema=MelodyOutput,
            input_fields=(
                "user_request",
                "creative_brief",
                "instructions_for_agents",
                "lyrics",
            ),
        )
