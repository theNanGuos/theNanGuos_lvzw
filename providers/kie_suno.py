import asyncio
import os
import re
import time
from pathlib import Path

import httpx

from providers.base import GeneratedTrack


class ProviderError(RuntimeError):
    pass


class KieSunoProvider:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key or os.getenv("KIE_API_KEY")
        if not self.api_key:
            raise ValueError("KIE_API_KEY is required to generate music")
        self.base_url = (base_url or os.getenv("KIE_BASE_URL", "https://api.kie.ai")).rstrip("/")
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=120)

    async def generate(
        self,
        prompt: str,
        output_dir: Path | str = "works",
        *,
        instrumental: bool = False,
    ) -> list[GeneratedTrack]:
        task_id = await self.submit(prompt, instrumental=instrumental)
        task = await self.wait(task_id)
        tracks = self.extract_tracks(task)
        if not tracks:
            raise ProviderError("Generation completed without audio tracks")
        return await self.download_tracks(tracks, output_dir)

    async def submit(self, prompt: str, *, instrumental: bool = False) -> str:
        payload = {
            "prompt": prompt,
            "customMode": False,
            "instrumental": instrumental,
            "model": os.getenv("KIE_MODEL", "V4"),
        }
        callback_url = os.getenv("KIE_CALLBACK_URL")
        if callback_url:
            payload["callBackUrl"] = callback_url
        data = await self._request_json("POST", "/api/v1/generate", json=payload)
        try:
            return data["data"]["taskId"]
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"Provider response does not contain taskId: {data}") from exc

    async def get_task(self, task_id: str) -> dict:
        data = await self._request_json(
            "GET",
            "/api/v1/generate/record-info",
            params={"taskId": task_id},
        )
        try:
            return data["data"]
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"Provider response does not contain task data: {data}") from exc

    async def wait(self, task_id: str, timeout_seconds: int = 15 * 60) -> dict:
        started_at = time.monotonic()
        while True:
            task = await self.get_task(task_id)
            task_status = str(task.get("status", "")).lower()
            if task_status == "success":
                return task
            if task_status == "fail":
                raise ProviderError(f"Music generation failed: {task}")
            elapsed = time.monotonic() - started_at
            if elapsed > timeout_seconds:
                raise TimeoutError(f"Music generation timed out: {task_id}")
            await asyncio.sleep(self.poll_interval(elapsed))

    async def download_tracks(
        self,
        tracks: list[tuple[str, str]],
        output_dir: Path | str,
    ) -> list[GeneratedTrack]:
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        results = []
        used_names: set[str] = set()
        for index, (title, url) in enumerate(tracks, start=1):
            stem = self.safe_filename(title) or f"track-{index}"
            unique_stem = stem
            suffix = 2
            while unique_stem in used_names:
                unique_stem = f"{stem}-{suffix}"
                suffix += 1
            used_names.add(unique_stem)
            path = directory / f"{unique_stem}.mp3"
            response = await self.client.get(url)
            response.raise_for_status()
            path.write_bytes(response.content)
            results.append(GeneratedTrack(title=title, source_url=url, local_path=path))
        return results

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def _request_json(self, method: str, path: str, **kwargs) -> dict:
        response = await self.client.request(
            method,
            f"{self.base_url}{path}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            **kwargs,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != 200:
            raise ProviderError(f"Provider request failed: {data}")
        return data

    @staticmethod
    def extract_tracks(task: dict) -> list[tuple[str, str]]:
        suno_data = task.get("response", {}).get("sunoData", [])
        return [
            (str(item.get("title") or "untitled"), item["audioUrl"])
            for item in suno_data
            if item.get("audioUrl")
        ]

    @staticmethod
    def safe_filename(title: str) -> str:
        cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", "-", title).strip(" .-")
        return cleaned[:80]

    @staticmethod
    def poll_interval(elapsed: float) -> int:
        if elapsed < 30:
            return 3
        if elapsed < 120:
            return 8
        return 20
