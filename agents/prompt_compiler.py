from langchain_core.language_models.chat_models import BaseChatModel

from agents.base import Agent
from lib.prompt import prompt_compiler
from models.state import PromptOutput


class PromptCompilerAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name="Prompt Compiler Agent",
            llm=llm,
            system_prompt=prompt_compiler(),
            output_schema=PromptOutput,
            input_fields=(
                "user_request",
                "creative_brief",
                "lyrics",
                "melody_plan",
                "arrangement_plan",
            ),
        )
