from pathlib import Path

from pydantic import BaseModel

from tools.audio import run_command


class DemoAudio(BaseModel):
    prompt: str
    output_path: str
    duration_seconds: float
    tempo_bpm: int
    frequencies: list[int]
    size_bytes: int = 0


def render_prompt_demo_audio(
    prompt: str,
    output_path: Path | str,
    *,
    duration_seconds: float = 12,
    tempo_bpm: int = 96,
    timeout_seconds: int = 120,
) -> DemoAudio:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frequencies = _frequencies_from_prompt(prompt)
    inputs = []
    labels = []
    for index, frequency in enumerate(frequencies):
        inputs.extend(
            [
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency={frequency}:duration={duration_seconds}",
            ]
        )
        labels.append(f"[{index}:a]")
    filter_graph = (
        f"{''.join(labels)}amix=inputs={len(frequencies)}:normalize=1,"
        "volume=0.22,"
        "afade=t=in:st=0:d=0.2,"
        f"afade=t=out:st={max(duration_seconds - 1, 0)}:d=1"
    )
    run_command(
        [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            filter_graph,
            "-ar",
            "44100",
            "-ac",
            "2",
            str(output),
        ],
        timeout_seconds=timeout_seconds,
    )
    return DemoAudio(
        prompt=prompt,
        output_path=str(output),
        duration_seconds=duration_seconds,
        tempo_bpm=tempo_bpm,
        frequencies=frequencies,
        size_bytes=output.stat().st_size if output.is_file() else 0,
    )


def _frequencies_from_prompt(prompt: str) -> list[int]:
    palette = [220, 247, 262, 294, 330, 349, 392, 440, 494, 523, 587, 659]
    seed = sum(ord(char) for char in prompt) or 440
    root = palette[seed % len(palette)]
    third = palette[(seed + 4) % len(palette)]
    fifth = palette[(seed + 7) % len(palette)]
    return [root, third, fifth]
