import asyncio
from pathlib import Path

from dotenv import load_dotenv

from providers.base import GeneratedTrack
from providers.kie_suno import KieSunoProvider


async def generate_async(
    prompt: str,
    output_dir: Path | str = "works",
    *,
    instrumental: bool = False,
    style: str | None = None,
    title: str | None = None,
) -> list[GeneratedTrack]:
    load_dotenv()
    provider = KieSunoProvider()
    try:
        return await provider.generate(
            prompt,
            output_dir,
            instrumental=instrumental,
            style=style,
            title=title,
        )
    finally:
        await provider.aclose()


def generate(
    prompt: str,
    output_dir: Path | str = "works",
    *,
    instrumental: bool = False,
    style: str | None = None,
    title: str | None = None,
) -> list[GeneratedTrack]:
    return asyncio.run(
        generate_async(
            prompt,
            output_dir,
            instrumental=instrumental,
            style=style,
            title=title,
        )
    )
