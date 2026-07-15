import json
import subprocess

import pytest

from tools.audio import (
    ToolExecutionError,
    inspect_audio,
    render_waveform,
    trim_audio_preview,
)
from tools.demo_audio import render_prompt_demo_audio


def test_inspect_audio_parses_ffprobe_json(monkeypatch, tmp_path):
    audio = tmp_path / "song.mp3"
    audio.write_bytes(b"audio")
    payload = {
        "streams": [
            {
                "codec_type": "audio",
                "codec_name": "mp3",
                "sample_rate": "44100",
                "channels": 2,
                "duration": "12.5",
                "bit_rate": "192000",
            }
        ],
        "format": {
            "format_name": "mp3",
            "size": "12345",
        },
    }

    def fake_run(command, **kwargs):
        assert command[:2] == ["ffprobe", "-v"]
        assert command[-1] == str(audio)
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = inspect_audio(audio)

    assert result.path == str(audio)
    assert result.duration_seconds == 12.5
    assert result.codec_name == "mp3"
    assert result.sample_rate == 44100
    assert result.channels == 2
    assert result.bit_rate == 192000
    assert result.size_bytes == 12345


def test_trim_audio_preview_invokes_ffmpeg(monkeypatch, tmp_path):
    source = tmp_path / "source.wav"
    output = tmp_path / "preview.mp3"
    source.write_bytes(b"source")
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        output.write_bytes(b"preview")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = trim_audio_preview(source, output, duration_seconds=15)

    assert commands[0][0] == "ffmpeg"
    assert "-t" in commands[0]
    assert "15" in commands[0]
    assert result.output_path == str(output)
    assert result.size_bytes == len(b"preview")


def test_render_waveform_invokes_showwavespic(monkeypatch, tmp_path):
    source = tmp_path / "source.mp3"
    output = tmp_path / "waveform.png"
    source.write_bytes(b"source")

    def fake_run(command, **kwargs):
        assert command[0] == "ffmpeg"
        assert any("showwavespic=s=640x180" in item for item in command)
        output.write_bytes(b"png")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = render_waveform(source, output, width=640, height=180)

    assert result.output_path == str(output)
    assert result.width == 640
    assert result.height == 180


def test_render_prompt_demo_audio_invokes_ffmpeg(monkeypatch, tmp_path):
    output = tmp_path / "demo.wav"

    def fake_run(command, **kwargs):
        assert command[0] == "ffmpeg"
        assert "-filter_complex" in command
        assert any("sine=frequency=" in item for item in command)
        output.write_bytes(b"demo")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = render_prompt_demo_audio("温暖流行歌", output, duration_seconds=8, tempo_bpm=108)

    assert result.output_path == str(output)
    assert result.duration_seconds == 8
    assert result.tempo_bpm == 108
    assert len(result.frequencies) == 3


def test_command_errors_are_reported(monkeypatch, tmp_path):
    def fake_run(command, **kwargs):
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(ToolExecutionError, match="Required command not found"):
        inspect_audio(tmp_path / "missing.mp3")
