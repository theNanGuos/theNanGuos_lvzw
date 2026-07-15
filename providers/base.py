from pathlib import Path
from typing import Protocol

from pydantic import BaseModel


class GeneratedTrack(BaseModel):
    title: str
    source_url: str
    local_path: Path
    cover_source_url: str | None = None
    cover_path: Path | None = None
    style: str | None = None
    duration_seconds: float | None = None


class MusicGenerationProvider(Protocol):
    async def generate(
        self,
        prompt: str,
        output_dir: Path | str,
        *,
        instrumental: bool = False,
        style: str | None = None,
        title: str | None = None,
        custom_mode: bool | None = None,
    ) -> list[GeneratedTrack]: ...
