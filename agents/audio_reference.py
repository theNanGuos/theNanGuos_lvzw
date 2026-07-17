import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool

from lib.logging_config import get_logger, log_context
from models.state import AudioReference, State
from tools.audio import (
    ToolExecutionError,
    inspect_audio,
    render_waveform,
    trim_audio_preview,
)

logger = get_logger(__name__)


@dataclass
class AudioReferenceAgent:
    llm: BaseChatModel

    def __call__(self, state: State) -> dict:
        paths = [Path(path) for path in state.get("reference_audio_paths", [])]
        if not paths:
            return {}
        if not hasattr(self.llm, "bind_tools"):
            logger.warning("audio_reference_skipped reason=llm_has_no_bind_tools")
            return {"audio_references": []}

        output_dir = Path(state.get("artifact_dir") or paths[0].parent) / "audio_tools"
        tools = self._build_tools(paths, output_dir)
        tool_by_name = {tool.name: tool for tool in tools}
        messages = [
            SystemMessage(
                content=(
                    "你是“参考南郭”，负责通过工具调用分析用户上传的音频。"
                    "只能使用提供的工具和 asset_index，不要请求任意文件路径。"
                    "优先调用 inspect_uploaded_audio；需要预览或可视化时再调用其他工具。"
                )
            ),
            HumanMessage(
                content=json.dumps(
                    {
                        "uploaded_assets": [
                            {"asset_index": index, "filename": path.name}
                            for index, path in enumerate(paths)
                        ]
                    },
                    ensure_ascii=False,
                )
            ),
        ]
        with log_context(stage="参考南郭"):
            logger.info("audio_reference_started assets=%s", len(paths))
            response = self.llm.bind_tools(tools).invoke(messages)
            references = []
            for call in getattr(response, "tool_calls", []) or []:
                name = call.get("name")
                args = call.get("args") or {}
                tool = tool_by_name.get(name)
                if tool is None:
                    logger.warning("audio_reference_unknown_tool name=%s", name)
                    continue
                result = tool.invoke(args)
                references.append(
                    AudioReference(
                        tool=name,
                        asset_index=int(args.get("asset_index", 0)),
                        result=result,
                    )
                )
            logger.info("audio_reference_completed tool_calls=%s", len(references))
        return {"audio_references": references}

    def _build_tools(self, paths: list[Path], output_dir: Path) -> list[StructuredTool]:
        def safe_call(asset_index: int, action: Callable[[Path, int], dict]) -> dict:
            if asset_index < 0 or asset_index >= len(paths):
                return {"error": f"asset_index {asset_index} is out of range"}
            try:
                return action(paths[asset_index], asset_index)
            except ToolExecutionError as exc:
                return {"error": str(exc)}

        def inspect_uploaded_audio(asset_index: int) -> dict:
            """Inspect an uploaded audio file with ffprobe by asset index."""
            return safe_call(
                asset_index,
                lambda path, _: inspect_audio(path).model_dump(mode="json"),
            )

        def create_uploaded_audio_preview(asset_index: int) -> dict:
            """Create a short normalized preview clip for an uploaded audio file."""
            return safe_call(
                asset_index,
                lambda path, index: trim_audio_preview(
                    path,
                    output_dir / f"reference-{index}-preview.mp3",
                ).model_dump(mode="json"),
            )

        def render_uploaded_audio_waveform(asset_index: int) -> dict:
            """Render a waveform image for an uploaded audio file."""
            return safe_call(
                asset_index,
                lambda path, index: render_waveform(
                    path,
                    output_dir / f"reference-{index}-waveform.png",
                ).model_dump(mode="json"),
            )

        return [
            StructuredTool.from_function(inspect_uploaded_audio),
            StructuredTool.from_function(create_uploaded_audio_preview),
            StructuredTool.from_function(render_uploaded_audio_waveform),
        ]
