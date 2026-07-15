import json
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ToolExecutionError(RuntimeError):
    pass


class AudioInspection(BaseModel):
    path: str
    duration_seconds: float | None = None
    format_name: str = ""
    codec_name: str = ""
    sample_rate: int | None = None
    channels: int | None = None
    bit_rate: int | None = None
    size_bytes: int = 0


class AudioPreview(BaseModel):
    source_path: str
    output_path: str
    duration_seconds: float
    size_bytes: int = 0


class WaveformImage(BaseModel):
    source_path: str
    output_path: str
    width: int
    height: int
    size_bytes: int = 0


class GeneratedAudioSummary(BaseModel):
    inspection: AudioInspection
    waveform_path: str | None = None


def run_command(command: list[str], timeout_seconds: int = 60) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        raise ToolExecutionError(f"Required command not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ToolExecutionError(f"Command timed out at stage {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise ToolExecutionError(f"Command failed at stage {command[0]}: {stderr}") from exc


def inspect_audio(path: Path | str, timeout_seconds: int = 30) -> AudioInspection:
    audio_path = Path(path)
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(audio_path),
        ],
        timeout_seconds=timeout_seconds,
    )
    data = json.loads(result.stdout)
    return _inspection_from_ffprobe(audio_path, data)


def trim_audio_preview(
    input_path: Path | str,
    output_path: Path | str,
    *,
    duration_seconds: float = 30,
    timeout_seconds: int = 120,
) -> AudioPreview:
    source = Path(input_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-t",
            str(duration_seconds),
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-af",
            "loudnorm",
            str(output),
        ],
        timeout_seconds=timeout_seconds,
    )
    return AudioPreview(
        source_path=str(source),
        output_path=str(output),
        duration_seconds=duration_seconds,
        size_bytes=_file_size(output),
    )


def render_waveform(
    input_path: Path | str,
    output_path: Path | str,
    *,
    width: int = 1280,
    height: int = 320,
    color: str = "#24745a",
    timeout_seconds: int = 120,
) -> WaveformImage:
    source = Path(input_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-filter_complex",
            f"showwavespic=s={width}x{height}:colors={color}",
            "-frames:v",
            "1",
            str(output),
        ],
        timeout_seconds=timeout_seconds,
    )
    return WaveformImage(
        source_path=str(source),
        output_path=str(output),
        width=width,
        height=height,
        size_bytes=_file_size(output),
    )


def summarize_generated_audio(
    input_path: Path | str,
    *,
    waveform_path: Path | str | None = None,
) -> GeneratedAudioSummary:
    inspection = inspect_audio(input_path)
    rendered_waveform = None
    if waveform_path is not None:
        rendered_waveform = render_waveform(input_path, waveform_path).output_path
    return GeneratedAudioSummary(
        inspection=inspection,
        waveform_path=rendered_waveform,
    )


def _inspection_from_ffprobe(path: Path, data: dict[str, Any]) -> AudioInspection:
    streams = data.get("streams") or []
    audio_stream = next(
        (stream for stream in streams if stream.get("codec_type") == "audio"),
        streams[0] if streams else {},
    )
    format_data = data.get("format") or {}
    duration = _number(audio_stream.get("duration")) or _number(format_data.get("duration"))
    bit_rate = _integer(audio_stream.get("bit_rate")) or _integer(format_data.get("bit_rate"))
    size_bytes = _integer(format_data.get("size")) or _file_size(path)
    return AudioInspection(
        path=str(path),
        duration_seconds=duration,
        format_name=str(format_data.get("format_name") or ""),
        codec_name=str(audio_stream.get("codec_name") or ""),
        sample_rate=_integer(audio_stream.get("sample_rate")),
        channels=_integer(audio_stream.get("channels")),
        bit_rate=bit_rate,
        size_bytes=size_bytes,
    )


def _number(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _integer(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def _file_size(path: Path) -> int:
    return path.stat().st_size if path.is_file() else 0
