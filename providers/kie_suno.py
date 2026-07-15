import asyncio
import os
import re
import time
from pathlib import Path

import httpx

from lib.logging_config import get_logger, log_context
from providers.base import GeneratedTrack


class ProviderError(RuntimeError):
    pass


FAILED_STATUSES = {
    "CREATE_TASK_FAILED",
    "GENERATE_AUDIO_FAILED",
    "CALLBACK_EXCEPTION",
    "SENSITIVE_WORD_ERROR",
}

PROMPT_LIMITS = {
    "V4": 3000,
    "V4_5": 5000,
    "V4_5PLUS": 5000,
    "V4_5ALL": 5000,
    "V5": 5000,
    "V5_5": 5000,
}

STYLE_LIMITS = {
    "V4": 200,
    "V4_5": 1000,
    "V4_5PLUS": 1000,
    "V4_5ALL": 1000,
    "V5": 1000,
    "V5_5": 1000,
}
logger = get_logger(__name__)


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
        self.model = os.getenv("KIE_MODEL", "V4")
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=120)

    async def generate(
        self,
        prompt: str,
        output_dir: Path | str = "works",
        *,
        instrumental: bool = False,
        style: str | None = None,
        title: str | None = None,
    ) -> list[GeneratedTrack]:
        logger.info(
            "music_generation_started instrumental=%s prompt_length=%s output_dir=%s",
            instrumental,
            len(prompt),
            output_dir,
        )
        task_id = await self.submit(
            prompt,
            instrumental=instrumental,
            style=style,
            title=title,
        )
        with log_context(run_id=task_id, stage="music_generation"):
            task = await self.wait(task_id)
            tracks = self.extract_tracks(task)
            if not tracks:
                logger.error("music_generation_no_tracks")
                raise ProviderError("Generation completed without audio tracks")
            downloaded = await self.download_tracks(tracks, output_dir)
            logger.info("music_generation_completed tracks=%s", len(downloaded))
            return downloaded

    async def submit(
        self,
        prompt: str,
        *,
        instrumental: bool = False,
        style: str | None = None,
        title: str | None = None,
        custom_mode: bool | None = None,
        callback_url: str | None = None,
        negative_tags: str | None = None,
        vocal_gender: str | None = None,
        style_weight: float | None = None,
        weirdness_constraint: float | None = None,
        audio_weight: float | None = None,
        persona_id: str | None = None,
        persona_model: str | None = None,
    ) -> str:
        model = self._validated_model()
        use_custom_mode = instrumental if custom_mode is None else custom_mode
        callback_url = callback_url or os.getenv("KIE_CALLBACK_URL")
        if not callback_url:
            raise ProviderError(
                "KIE_CALLBACK_URL is required by Kie Suno generate API; "
                "set it to a public endpoint that accepts generation callbacks"
            )

        payload = {
            "prompt": prompt,
            "customMode": use_custom_mode,
            "instrumental": instrumental,
            "model": model,
            "callBackUrl": callback_url,
        }
        if use_custom_mode:
            payload["style"] = (style or os.getenv("KIE_STYLE", "")).strip()
            payload["title"] = (title or os.getenv("KIE_TITLE") or self.default_title(prompt)).strip()
            self._validate_custom_payload(payload, model, instrumental)
            self._add_optional_custom_fields(
                payload,
                negative_tags=negative_tags,
                vocal_gender=vocal_gender,
                style_weight=style_weight,
                weirdness_constraint=weirdness_constraint,
                audio_weight=audio_weight,
                persona_id=persona_id,
                persona_model=persona_model,
            )
        elif len(prompt) > 500:
            raise ProviderError("Kie Suno non-custom mode prompt exceeds 500 characters")

        logger.info(
            "music_task_submit model=%s custom_mode=%s instrumental=%s prompt_length=%s",
            model,
            use_custom_mode,
            instrumental,
            len(prompt),
        )
        data = await self._request_json("POST", "/api/v1/generate", json=payload)
        try:
            task_id = data["data"]["taskId"]
            logger.info("music_task_submitted task_id=%s", task_id)
            return task_id
        except (KeyError, TypeError) as exc:
            logger.exception("music_task_missing_task_id")
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
            task_status = str(task.get("status", "")).upper()
            logger.info("music_task_polled status=%s", task_status or "UNKNOWN")
            if task_status == "SUCCESS":
                return task
            if task_status in FAILED_STATUSES:
                reason = task.get("errorMessage") or task.get("errorCode") or task
                logger.error("music_task_failed status=%s reason=%s", task_status, reason)
                raise ProviderError(f"Music generation failed at {task_status}: {reason}")
            elapsed = time.monotonic() - started_at
            if elapsed > timeout_seconds:
                logger.error("music_task_timeout task_id=%s", task_id)
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
            logger.info("music_track_downloaded title=%s path=%s size=%s", title, path, len(response.content))
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
            logger.error("provider_request_failed method=%s path=%s response=%s", method, path, data)
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

    def _validated_model(self) -> str:
        if self.model not in PROMPT_LIMITS:
            choices = ", ".join(PROMPT_LIMITS)
            raise ProviderError(f"Unsupported KIE_MODEL {self.model!r}; expected one of {choices}")
        return self.model

    @staticmethod
    def _validate_custom_payload(payload: dict, model: str, instrumental: bool) -> None:
        title = str(payload.get("title") or "")
        style = str(payload.get("style") or "")
        prompt = str(payload.get("prompt") or "")
        if not style:
            raise ProviderError("Kie Suno custom mode requires style; set KIE_STYLE or pass style")
        if not title:
            raise ProviderError("Kie Suno custom mode requires title; set KIE_TITLE or pass title")
        if len(title) > 80:
            raise ProviderError("Kie Suno title exceeds 80 characters")
        if len(style) > STYLE_LIMITS[model]:
            raise ProviderError(f"Kie Suno style exceeds {STYLE_LIMITS[model]} characters for {model}")
        if not instrumental and not prompt:
            raise ProviderError("Kie Suno custom vocal mode requires prompt lyrics")
        if len(prompt) > PROMPT_LIMITS[model]:
            raise ProviderError(f"Kie Suno prompt exceeds {PROMPT_LIMITS[model]} characters for {model}")

    @staticmethod
    def _add_optional_custom_fields(
        payload: dict,
        *,
        negative_tags: str | None,
        vocal_gender: str | None,
        style_weight: float | None,
        weirdness_constraint: float | None,
        audio_weight: float | None,
        persona_id: str | None,
        persona_model: str | None,
    ) -> None:
        if negative_tags:
            payload["negativeTags"] = negative_tags
        if vocal_gender:
            if vocal_gender not in {"m", "f"}:
                raise ProviderError("Kie Suno vocalGender must be 'm' or 'f'")
            payload["vocalGender"] = vocal_gender
        for field, value in (
            ("styleWeight", style_weight),
            ("weirdnessConstraint", weirdness_constraint),
            ("audioWeight", audio_weight),
        ):
            if value is None:
                continue
            if value < 0 or value > 1:
                raise ProviderError(f"Kie Suno {field} must be between 0 and 1")
            payload[field] = round(value, 2)
        if persona_id:
            payload["personaId"] = persona_id
        if persona_model:
            if persona_model not in {"style_persona", "voice_persona"}:
                raise ProviderError(
                    "Kie Suno personaModel must be 'style_persona' or 'voice_persona'"
                )
            payload["personaModel"] = persona_model

    @staticmethod
    def default_title(prompt: str) -> str:
        title = re.sub(r"\s+", " ", prompt).strip()
        return title[:80] or "Generated Music"
