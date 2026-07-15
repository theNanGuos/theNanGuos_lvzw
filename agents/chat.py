from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import chat
from models.chat import ChatDecision


class ChatAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="Chat Agent",
            llm=llm,
            system_prompt=chat(),
            output_schema=ChatDecision,
            input_fields=(
                "latest_message",
                "recent_messages",
                "session_summary",
                "active_project_id",
                "memory_context",
            ),
        )
