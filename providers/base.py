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
    ) -> list[GeneratedTrack]: ...
