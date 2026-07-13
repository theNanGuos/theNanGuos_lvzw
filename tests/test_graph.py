from collections import defaultdict, deque

from app.graph import build_graph
from models.state import (
    ArrangementOutput,
    ConductorOutput,
    LyricsOutput,
    MelodyOutput,
    PromptOutput,
)


class ScriptedStructuredModel:
    def __init__(self, responses):
        self.responses = defaultdict(deque)
        for response in responses:
            self.responses[type(response)].append(response)
        self.calls = []

    def with_structured_output(self, schema):
        model = self

        class Runner:
            def invoke(self, messages):
                model.calls.append(schema)
                return model.responses[schema].popleft()

        return Runner()


def conductor_output(workflow, vocal):
    return ConductorOutput.model_validate(
        {
            "workflow": workflow,
            "creative_brief": {
                "title": "测试作品",
                "language": "中文" if vocal else "instrumental",
                "genre": "流行" if vocal else "古典",
                "mood": ["温暖" if vocal else "恢弘"],
                "theme": "归途" if vocal else "远征",
                "duration_seconds": 90,
                "tempo_feel": "medium",
                "vocal": vocal,
                "vocal_style": "柔和女声" if vocal else "",
                "song_structure": ["intro", "verse", "chorus", "outro"],
                "production_style": "自然、清晰",
            },
            "instructions_for_agents": {},
        }
    )


def melody_output():
    return MelodyOutput.model_validate(
        {
            "melody_plan": {
                "tempo": "92 BPM",
                "melody_style": "逐步上行的歌唱性主题",
                "verse_melody": "平稳",
                "chorus_melody": "开阔",
                "hook": "短促上行主题",
                "harmony": "温暖的大调和声",
                "rhythm": "稳定四拍",
                "emotional_arc": "克制到明亮",
            }
        }
    )


def arrangement_output():
    return ArrangementOutput.model_validate(
        {
            "arrangement_plan": {
                "instrumentation": ["钢琴", "弦乐"],
                "section_development": "由稀疏逐渐丰满",
                "texture": "清晰分层",
                "production": "自然空间感",
            }
        }
    )


def test_pop_workflow_includes_lyrics():
    llm = ScriptedStructuredModel(
        [
            conductor_output("pop_vocal", vocal=True),
            LyricsOutput.model_validate(
                {
                    "lyrics": {
                        "verse": ["晚风送我回家"],
                        "chorus": ["灯火仍在等我"],
                        "language": "中文",
                        "theme": "归途",
                        "hook": "灯火仍在等我",
                        "singing_style_hint": "柔和",
                    }
                }
            ),
            melody_output(),
            arrangement_output(),
            PromptOutput(final_prompt="温暖中文流行，柔和女声，钢琴与弦乐渐进。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "写一首关于归途的歌"})

    assert result["workflow"] == "pop_vocal"
    assert result["lyrics"].hook == "灯火仍在等我"
    assert result["final_prompt"].startswith("温暖中文流行")
    assert LyricsOutput in llm.calls


def test_classical_workflow_skips_lyrics():
    llm = ScriptedStructuredModel(
        [
            conductor_output("classical_instrumental", vocal=False),
            melody_output(),
            arrangement_output(),
            PromptOutput(final_prompt="恢弘古典器乐，钢琴与弦乐展开远征主题，无人声。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "生成一首恢弘的钢琴协奏曲"})

    assert result["workflow"] == "classical_instrumental"
    assert "lyrics" not in result
    assert "无人声" in result["final_prompt"]
    assert LyricsOutput not in llm.calls
