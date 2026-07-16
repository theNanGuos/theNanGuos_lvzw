import json

import httpx
import pytest

from providers.kie_suno import (
    PROMPT_LIMITS,
    STYLE_LIMITS,
    KieSunoProvider,
    ProviderError,
    text_length,
)


@pytest.fixture(autouse=True)
def clean_kie_env(monkeypatch):
    for name in ("KIE_MODEL", "KIE_CALLBACK_URL", "KIE_STYLE", "KIE_TITLE"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.asyncio
async def test_kie_provider_generates_and_downloads_tracks(tmp_path, monkeypatch):
    requests = []
    monkeypatch.setenv("KIE_CALLBACK_URL", "https://app.test/kie/callback")

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v1/generate":
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "task-1"}})
        if request.url.path == "/api/v1/generate/record-info":
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "status": "SUCCESS",
                        "response": {
                            "sunoData": [
                                {
                                    "title": "夜/曲",
                                    "audioUrl": "https://audio.test/one",
                                    "imageUrl": "https://image.test/one.jpg",
                                    "duration": 123.5,
                                    "tags": "cinematic piano",
                                },
                                {
                                    "title": "夜/曲",
                                    "audioUrl": "https://audio.test/two",
                                    "imageUrl": "https://image.test/two.png",
                                },
                            ]
                        },
                    },
                },
            )
        if request.url.host == "audio.test":
            return httpx.Response(200, content=b"mp3 data")
        if request.url.host == "image.test":
            content_type = "image/png" if request.url.path.endswith(".png") else "image/jpeg"
            return httpx.Response(200, content=b"cover data", headers={"content-type": content_type})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = KieSunoProvider(
        api_key="test-key",
        base_url="https://provider.test",
        client=client,
    )

    tracks = await provider.generate(
        "instrumental prompt",
        tmp_path,
        instrumental=True,
        style="Classical",
        title="Night Song",
    )

    assert [track.local_path.name for track in tracks] == ["夜-曲.mp3", "夜-曲-2.mp3"]
    assert [track.cover_path.name for track in tracks] == ["夜-曲.jpg", "夜-曲-2.png"]
    assert all(track.local_path.read_bytes() == b"mp3 data" for track in tracks)
    assert all(track.cover_path.read_bytes() == b"cover data" for track in tracks)
    assert tracks[0].duration_seconds == 123.5
    assert tracks[0].style == "cinematic piano"
    submit_payload = json.loads(requests[0].content)
    assert submit_payload["customMode"] is True
    assert submit_payload["instrumental"] is True
    assert submit_payload["model"] == "V4"
    assert submit_payload["callBackUrl"] == "https://app.test/kie/callback"
    assert submit_payload["style"] == "Classical"
    assert submit_payload["title"] == "Night Song"
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    await client.aclose()


@pytest.mark.asyncio
async def test_kie_provider_reports_api_errors():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"code": 401, "msg": "invalid key"})
    )
    client = httpx.AsyncClient(transport=transport)
    provider = KieSunoProvider(api_key="bad-key", client=client)

    with pytest.raises(ProviderError, match="invalid key"):
        await provider.submit("prompt", callback_url="https://app.test/kie/callback")

    await client.aclose()


@pytest.mark.asyncio
async def test_kie_provider_non_custom_payload_leaves_custom_fields_empty():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"code": 200, "data": {"taskId": "task-1"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = KieSunoProvider(api_key="test-key", client=client)

    task_id = await provider.submit(
        "short song idea",
        callback_url="https://app.test/kie/callback",
    )

    assert task_id == "task-1"
    submit_payload = json.loads(requests[0].content)
    assert submit_payload == {
        "prompt": "short song idea",
        "customMode": False,
        "instrumental": False,
        "model": "V4",
        "callBackUrl": "https://app.test/kie/callback",
    }
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("model", list(PROMPT_LIMITS))
async def test_kie_provider_truncates_custom_fields_to_model_limits(monkeypatch, model):
    requests = []
    monkeypatch.setenv("KIE_MODEL", model)

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"code": 200, "data": {"taskId": "task-1"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = KieSunoProvider(api_key="test-key", client=client)

    await provider.submit(
        "音" * (PROMPT_LIMITS[model] + 1),
        instrumental=True,
        custom_mode=True,
        style="风" * (STYLE_LIMITS[model] + 1),
        title="题" * 81,
        callback_url="https://app.test/kie/callback",
    )

    payload = json.loads(requests[0].content)
    assert text_length(payload["prompt"]) == PROMPT_LIMITS[model]
    assert text_length(payload["style"]) == STYLE_LIMITS[model]
    assert text_length(payload["title"]) == 80
    await client.aclose()


@pytest.mark.asyncio
async def test_kie_provider_truncates_non_custom_prompt_and_omits_custom_fields():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"code": 200, "data": {"taskId": "task-1"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = KieSunoProvider(api_key="test-key", client=client)

    await provider.submit(
        "idea " * 200,
        instrumental=True,
        custom_mode=False,
        style="ignored style",
        title="ignored title",
        callback_url="https://app.test/kie/callback",
    )

    payload = json.loads(requests[0].content)
    assert text_length(payload["prompt"]) == 500
    assert "style" not in payload
    assert "title" not in payload
    await client.aclose()


@pytest.mark.asyncio
async def test_kie_provider_counts_emoji_conservatively_when_truncating():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"code": 200, "data": {"taskId": "task-1"}})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = KieSunoProvider(api_key="test-key", client=client)

    await provider.submit(
        "prompt",
        instrumental=True,
        style="🎵" * 101,
        title="title",
        callback_url="https://app.test/kie/callback",
    )

    payload = json.loads(requests[0].content)
    assert payload["style"] == "🎵" * 100
    assert text_length(payload["style"]) == 200
    await client.aclose()


@pytest.mark.asyncio
async def test_kie_provider_requires_callback_url():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(500)))
    provider = KieSunoProvider(api_key="test-key", client=client)

    with pytest.raises(ProviderError, match="KIE_CALLBACK_URL"):
        await provider.submit("short song idea")

    await client.aclose()


@pytest.mark.asyncio
async def test_kie_provider_reports_failed_task_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "status": "SENSITIVE_WORD_ERROR",
                    "errorMessage": "content filtered",
                },
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = KieSunoProvider(api_key="test-key", client=client)

    with pytest.raises(ProviderError, match="SENSITIVE_WORD_ERROR"):
        await provider.wait("task-1")

    await client.aclose()
