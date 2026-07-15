from pathlib import Path
from typing import Protocol

from pydantic import BaseModel


class GeneratedTrack(BaseModel):
    title: str
    source_url: str
    local_path: Path


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
