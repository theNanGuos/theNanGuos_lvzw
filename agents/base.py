import json
from abc import ABC
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from models.state import State


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


@dataclass
class Agent(ABC):
    name: str
    system_prompt: str
    llm: BaseChatModel
    output_schema: type[BaseModel]
    input_fields: tuple[str, ...]

    def __call__(self, state: State) -> dict:
        payload = {
            field: _json_value(state[field])
            for field in self.input_fields
            if field in state
        }
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        response = self.llm.with_structured_output(self.output_schema).invoke(messages)
        if not isinstance(response, self.output_schema):
            response = self.output_schema.model_validate(response)
        return {
            field: getattr(response, field)
            for field in type(response).model_fields
        }
