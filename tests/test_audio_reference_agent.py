from langchain_core.messages import AIMessage

from agents.audio_reference import AudioReferenceAgent


class ToolCallingModel:
    def __init__(self):
        self.tools = []
        self.messages = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    def invoke(self, messages):
        self.messages = messages
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "inspect_uploaded_audio",
                    "args": {"asset_index": 0},
                    "id": "call-1",
                }
            ],
        )


def test_audio_reference_agent_uses_llm_tool_calling(monkeypatch, tmp_path):
    audio = tmp_path / "reference.mp3"
    audio.write_bytes(b"audio")

    class FakeInspection:
        def model_dump(self, mode=None):
            return {
                "path": str(audio),
                "duration_seconds": 12.5,
                "codec_name": "mp3",
            }

    monkeypatch.setattr(
        "agents.audio_reference.inspect_audio",
        lambda path: FakeInspection(),
    )
    model = ToolCallingModel()
    agent = AudioReferenceAgent(model)

    result = agent(
        {
            "reference_audio_paths": [str(audio)],
            "artifact_dir": str(tmp_path / "artifacts"),
        }
    )

    assert [tool.name for tool in model.tools] == [
        "inspect_uploaded_audio",
        "create_uploaded_audio_preview",
        "render_uploaded_audio_waveform",
    ]
    assert result["audio_references"][0].tool == "inspect_uploaded_audio"
    assert result["audio_references"][0].asset_index == 0
    assert result["audio_references"][0].result["duration_seconds"] == 12.5


def test_audio_reference_agent_skips_without_assets():
    agent = AudioReferenceAgent(ToolCallingModel())

    assert agent({}) == {}
