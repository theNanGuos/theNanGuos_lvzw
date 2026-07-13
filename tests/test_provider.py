import json

import httpx
import pytest

from providers.kie_suno import KieSunoProvider, ProviderError


@pytest.mark.asyncio
async def test_kie_provider_generates_and_downloads_tracks(tmp_path):
    requests = []

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
                        "status": "success",
                        "response": {
                            "sunoData": [
                                {"title": "夜/曲", "audioUrl": "https://audio.test/one"},
                                {"title": "夜/曲", "audioUrl": "https://audio.test/two"},
                            ]
                        },
                    },
                },
            )
        if request.url.host == "audio.test":
            return httpx.Response(200, content=b"mp3 data")
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = KieSunoProvider(
        api_key="test-key",
        base_url="https://provider.test",
        client=client,
    )

    tracks = await provider.generate("instrumental prompt", tmp_path, instrumental=True)

    assert [track.local_path.name for track in tracks] == ["夜-曲.mp3", "夜-曲-2.mp3"]
    assert all(track.local_path.read_bytes() == b"mp3 data" for track in tracks)
    submit_payload = json.loads(requests[0].content)
    assert submit_payload["instrumental"] is True
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
        await provider.submit("prompt")

    await client.aclose()
