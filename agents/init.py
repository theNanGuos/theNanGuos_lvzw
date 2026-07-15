import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel


def _message_role(message: BaseMessage) -> str:
    if isinstance(message, SystemMessage):
        return "system"
    if isinstance(message, HumanMessage):
        return "user"
    if isinstance(message, AIMessage):
        return "assistant"
    return getattr(message, "type", "user")


def _message_content(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return str(content)


@dataclass
class OpenAICompatibleChat:
    model: str
    api_key: str
    base_url: str
    timeout: float = 120.0
    max_retries: int = 2
    client: httpx.Client | None = None

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": _message_role(message),
                    "content": _message_content(message),
                }
                for message in messages
            ],
        }
        last_error: RuntimeError | None = None
        for attempt in range(self.max_retries + 1):
            response = self._client().post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            try:
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("response body was not a JSON object")
                choices = data.get("choices") or []
                message = choices[0]["message"]
                content = message.get("content")
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("response message content was empty")
                return AIMessage(content=content)
            except Exception as exc:
                body = response.text[:500]
                last_error = RuntimeError(
                    f"OpenAI-compatible chat request failed: "
                    f"status={response.status_code}, body={body}"
                )
                if response.status_code < 500 and attempt >= self.max_retries:
                    raise last_error from exc
                if attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise last_error from exc
        raise last_error or RuntimeError("OpenAI-compatible chat request failed")

    def with_structured_output(self, schema: type[BaseModel], **_: Any):
        model = self

        class Runner:
            def invoke(self, messages: list[BaseMessage]) -> BaseModel:
                response = model.invoke(messages)
                return schema.model_validate_json(response.content)

        return Runner()

    def _client(self) -> httpx.Client:
        if self.client is not None:
            return self.client
        self.client = httpx.Client(timeout=self.timeout)
        return self.client


def create_llm() -> OpenAICompatibleChat | ChatOpenAI:
    load_dotenv(".env")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    if not api_key or not base_url:
        raise RuntimeError("OPENAI_API_KEY and OPENAI_BASE_URL must be set")

    method = os.getenv("LLM_STRUCTURED_OUTPUT_METHOD", "prompt_json")
    if method in {"function_calling", "json_schema"}:
        return ChatOpenAI(
            model=os.getenv("MODEL_NAME", "glm-5.1"),
            api_key=api_key,
            base_url=base_url,
        )

    return OpenAICompatibleChat(
        model=os.getenv("MODEL_NAME", "glm-5.1"),
        api_key=api_key,
        base_url=base_url,
        max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
    )
