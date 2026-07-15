import json
import os
import re
from abc import ABC
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from lib.logging_config import get_logger, log_context
from models.state import State

STRUCTURED_OUTPUT_METHODS = {"prompt_json", "json_mode", "function_calling", "json_schema"}
logger = get_logger(__name__)


def _json_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _structured_output_method() -> str:
    method = os.getenv("LLM_STRUCTURED_OUTPUT_METHOD", "prompt_json")
    if method not in STRUCTURED_OUTPUT_METHODS:
        choices = ", ".join(sorted(STRUCTURED_OUTPUT_METHODS))
        raise ValueError(f"LLM_STRUCTURED_OUTPUT_METHOD must be one of: {choices}")
    return method


def _message_text(response: object) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError(f"Model response did not contain a JSON object: {text[:300]}")


@dataclass
class Agent(ABC):
    name: str
    system_prompt: str
    llm: BaseChatModel
    output_schema: type[BaseModel]
    input_fields: tuple[str, ...]

    def fallback(self, state: State, exc: Exception) -> BaseModel | None:
        return None

    def __call__(self, state: State) -> dict:
        payload = {
            field: _json_value(state[field])
            for field in self.input_fields
            if field in state
        }
        schema_json = json.dumps(
            self.output_schema.model_json_schema(),
            ensure_ascii=False,
        )
        system_prompt = (
            f"{self.system_prompt}\n\n"
            "必须只返回一个 JSON object，字段和值必须符合下面的 JSON Schema。"
            "不要使用 Markdown，不要包裹代码块，不要输出解释。\n"
            f"{schema_json}"
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        method = _structured_output_method()
        try:
            with log_context(stage=self.name):
                logger.info(
                    "agent_started name=%s method=%s input_fields=%s",
                    self.name,
                    method,
                    ",".join(payload),
                )
                if method in {"prompt_json", "json_mode"}:
                    raw_response = self.llm.invoke(messages)
                    response = _extract_json_object(_message_text(raw_response))
                else:
                    try:
                        runner = self.llm.with_structured_output(
                            self.output_schema,
                            method=method,
                        )
                    except TypeError:
                        runner = self.llm.with_structured_output(self.output_schema)
                    response = runner.invoke(messages)
                if not isinstance(response, self.output_schema):
                    response = self.output_schema.model_validate(response)
                logger.info("agent_completed name=%s", self.name)
        except Exception as exc:
            fallback = self.fallback(state, exc)
            if fallback is None:
                logger.exception("agent_failed name=%s", self.name)
                raise RuntimeError(
                    f"{self.name} failed to produce valid structured output: {exc}"
                ) from exc
            logger.warning("agent_fallback_used name=%s reason=%s", self.name, exc)
            response = fallback
        return {
            field: getattr(response, field)
            for field in type(response).model_fields
        }
