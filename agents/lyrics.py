from agents.base import Agent
from langchain_core.language_models.chat_models import BaseChatModel
from lib.prompt import lyrics
from models.state import LyricsOutput

class LyricsAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name = "Lyrics Agent",
            llm = llm,
            system_prompt = (
                lyrics()
            ),
            output_schema=LyricsOutput,
            input_fields=("user_request", "creative_brief", "instructions_for_agents"),
        )
