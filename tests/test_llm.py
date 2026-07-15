import json

import httpx
import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.init import OpenAICompatibleChat, create_llm


def test_openai_compatible_chat_reads_message_content():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": '{"final_prompt":"轻快流行，明亮旋律。"}',
                        }
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    llm = OpenAICompatibleChat(
        model="test-model",
        api_key="test-key",
        base_url="https://llm.test/v1",
        max_retries=0,
        client=client,
    )

    response = llm.invoke(
        [
            SystemMessage(content="只返回 JSON"),
            HumanMessage(content="写一首歌"),
        ]
    )

    assert response.content == '{"final_prompt":"轻快流行，明亮旋律。"}'
    payload = json.loads(requests[0].content)
    assert requests[0].url == "https://llm.test/v1/chat/completions"
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    assert payload["model"] == "test-model"
    assert payload["messages"][0] == {"role": "system", "content": "只返回 JSON"}
    assert payload["messages"][1] == {"role": "user", "content": "写一首歌"}


def test_openai_compatible_chat_reports_malformed_response():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": None}))
    )
    llm = OpenAICompatibleChat(
        model="test-model",
        api_key="test-key",
        base_url="https://llm.test/v1",
        client=client,
    )

    with pytest.raises(RuntimeError, match="OpenAI-compatible chat request failed"):
        llm.invoke([HumanMessage(content="hello")])


def test_openai_compatible_chat_retries_null_response():
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(200, json=None)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    llm = OpenAICompatibleChat(
        model="test-model",
        api_key="test-key",
        base_url="https://llm.test/v1",
        max_retries=1,
        client=client,
    )

    response = llm.invoke([HumanMessage(content="hello")])

    assert response.content == '{"ok": true}'
    assert attempts == 2


def test_create_llm_uses_chat_openai_for_tool_calling(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://llm.test/v1")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("LLM_STRUCTURED_OUTPUT_METHOD", "function_calling")

    llm = create_llm()

    assert isinstance(llm, ChatOpenAI)
