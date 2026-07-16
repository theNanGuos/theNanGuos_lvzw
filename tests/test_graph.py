from collections import defaultdict, deque

from langchain_core.messages import AIMessage

from app.graph import build_graph
from models.state import (
    ArrangementOutput,
    ConductorOutput,
    HarmonyOutput,
    ImprovisationOutput,
    LyricsOutput,
    MelodyOutput,
    MixReviewOutput,
    PerformanceOutput,
    PromptOutput,
    RhythmOutput,
    SoundDesignOutput,
)


class ScriptedStructuredModel:
    def __init__(self, responses):
        self.responses = defaultdict(deque)
        for response in responses:
            self.responses[type(response)].append(response)
        self.response_queue = deque(responses)
        self.calls = []
        self.methods = []
        self.plain_invocations = 0

    def invoke(self, messages):
        self.plain_invocations += 1
        assert "JSON Schema" in messages[0].content
        response = self.response_queue.popleft()
        self.calls.append(type(response))
        return AIMessage(content=response.model_dump_json())

    def with_structured_output(self, schema, **kwargs):
        model = self
        model.methods.append(kwargs.get("method"))

        class Runner:
            def invoke(self, messages):
                model.calls.append(schema)
                assert "JSON Schema" in messages[0].content
                return model.responses[schema].popleft()

        return Runner()


class FencedJsonModel:
    def invoke(self, messages):
        assert "JSON Schema" in messages[0].content
        return AIMessage(
            content='```json\n{"final_prompt":"温暖民谣，木吉他，轻柔人声。"}\n```'
        )


class FailingAfterConductorModel:
    def __init__(self):
        self.first = True

    def invoke(self, messages):
        assert "JSON Schema" in messages[0].content
        if self.first:
            self.first = False
            return AIMessage(content=conductor_output("pop_vocal", vocal=True).model_dump_json())
        raise RuntimeError("status=200, body=null")


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


def lyrics_output():
    return LyricsOutput.model_validate(
        {
            "lyrics": {
                "verse": ["夜色沿着街道展开"],
                "chorus": ["让回声带我们向前"],
                "language": "中文",
                "theme": "出发",
                "hook": "带我们向前",
                "singing_style_hint": "有节奏感",
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


def harmony_output():
    return HarmonyOutput.model_validate(
        {
            "harmony_plan": {
                "key_center": "C major",
                "chord_progression": ["I", "V", "vi", "IV"],
                "harmonic_rhythm": "每两小节换和弦",
                "tension_strategy": "副歌增加明亮属功能回归",
            }
        }
    )


def rhythm_output():
    return RhythmOutput.model_validate(
        {
            "rhythm_plan": {
                "groove": "稳定四拍，副歌加入切分",
                "percussion": ["鼓组", "拍手"],
                "rhythmic_motifs": ["弱起", "切分强调"],
                "energy_curve": "逐段增强",
            }
        }
    )


def sound_design_output():
    return SoundDesignOutput.model_validate(
        {
            "sound_design_plan": {
                "palette": ["钢琴", "柔和 pad"],
                "signature_sounds": ["过门 swell"],
                "spatial_motion": "副歌拓宽声场",
                "texture_notes": "保持 hook 清晰",
            }
        }
    )


def mix_review_output():
    return MixReviewOutput.model_validate(
        {
            "mix_review": {
                "focus": "主旋律清晰",
                "balance_notes": ["低频稳定", "人声靠前"],
                "risk_checks": ["避免配器遮挡 hook"],
            }
        }
    )


def improvisation_output():
    return ImprovisationOutput.model_validate(
        {
            "improvisation_plan": {
                "soloists": ["萨克斯", "钢琴"],
                "solo_form": "主题后各一轮独奏并回到主题",
                "vocabulary": ["和弦音导向", "动机发展"],
                "ensemble_interaction": "节奏组根据独奏密度回应",
                "guardrails": ["保留主题动机"],
            }
        }
    )


def performance_output():
    return PerformanceOutput.model_validate(
        {
            "performance_plan": {
                "articulation": "短音清晰，长音保留呼吸",
                "dynamics": "逐段增强后自然回落",
                "ensemble_interaction": "鼓贝锁定并回应主奏",
                "humanization": ["自然力度差", "轻微时值浮动"],
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
            harmony_output(),
            rhythm_output(),
            arrangement_output(),
            sound_design_output(),
            mix_review_output(),
            PromptOutput(final_prompt="温暖中文流行，柔和女声，钢琴与弦乐渐进。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "写一首关于归途的歌"})

    assert result["workflow"] == "pop_vocal"
    assert result["lyrics"].hook == "灯火仍在等我"
    assert result["final_prompt"].startswith("温暖中文流行")
    assert LyricsOutput in llm.calls
    assert HarmonyOutput in llm.calls
    assert RhythmOutput in llm.calls
    assert SoundDesignOutput in llm.calls
    assert MixReviewOutput in llm.calls
    assert llm.plain_invocations == 9
    assert llm.methods == []


def test_classical_workflow_skips_lyrics():
    llm = ScriptedStructuredModel(
        [
            conductor_output("classical_instrumental", vocal=False),
            melody_output(),
            harmony_output(),
            arrangement_output(),
            sound_design_output(),
            mix_review_output(),
            PromptOutput(final_prompt="恢弘古典器乐，钢琴与弦乐展开远征主题，无人声。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "生成一首恢弘的钢琴协奏曲"})

    assert result["workflow"] == "classical_instrumental"
    assert "lyrics" not in result
    assert "无人声" in result["final_prompt"]
    assert LyricsOutput not in llm.calls
    assert RhythmOutput not in llm.calls


def test_electronic_workflow_starts_with_rhythm_and_skips_lyrics():
    llm = ScriptedStructuredModel(
        [
            conductor_output("electronic_instrumental", vocal=False),
            rhythm_output(),
            melody_output(),
            harmony_output(),
            arrangement_output(),
            sound_design_output(),
            mix_review_output(),
            PromptOutput(final_prompt="电子器乐，合成器低频，四拍律动，明亮空间感。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "生成一首电子器乐"})

    assert result["workflow"] == "electronic_instrumental"
    assert "lyrics" not in result
    assert llm.calls[:4] == [
        ConductorOutput,
        RhythmOutput,
        MelodyOutput,
        HarmonyOutput,
    ]


def test_soundtrack_workflow_uses_score_style_branch_without_rhythm():
    llm = ScriptedStructuredModel(
        [
            conductor_output("soundtrack_score", vocal=False),
            melody_output(),
            harmony_output(),
            arrangement_output(),
            sound_design_output(),
            mix_review_output(),
            PromptOutput(final_prompt="影视配乐，弦乐主题，宽广空间，情绪递进。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "生成一首电影感配乐"})

    assert result["workflow"] == "soundtrack_score"
    assert SoundDesignOutput in llm.calls
    assert RhythmOutput not in llm.calls


def test_jazz_workflow_builds_harmony_and_groove_before_improvisation():
    llm = ScriptedStructuredModel(
        [
            conductor_output("jazz_ensemble", vocal=False),
            harmony_output(),
            rhythm_output(),
            melody_output(),
            improvisation_output(),
            performance_output(),
            arrangement_output(),
            sound_design_output(),
            mix_review_output(),
            PromptOutput(final_prompt="爵士四重奏，swing 律动，萨克斯与钢琴即兴，无人声。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "创作一首有萨克斯即兴的爵士乐"})

    assert result["workflow"] == "jazz_ensemble"
    assert "lyrics" not in result
    assert result["improvisation_plan"].soloists == ["萨克斯", "钢琴"]
    assert llm.calls[:6] == [
        ConductorOutput,
        HarmonyOutput,
        RhythmOutput,
        MelodyOutput,
        ImprovisationOutput,
        PerformanceOutput,
    ]


def test_rock_workflow_adds_band_performance_after_rhythm():
    llm = ScriptedStructuredModel(
        [
            conductor_output("rock_vocal", vocal=True),
            lyrics_output(),
            melody_output(),
            harmony_output(),
            rhythm_output(),
            performance_output(),
            arrangement_output(),
            sound_design_output(),
            mix_review_output(),
            PromptOutput(final_prompt="中文摇滚，真实乐队动态，强力副歌。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "写一首热烈的中文摇滚"})

    assert result["workflow"] == "rock_vocal"
    assert result["lyrics"].hook
    assert llm.calls[4:6] == [RhythmOutput, PerformanceOutput]


def test_folk_workflow_prioritizes_story_and_acoustic_performance():
    llm = ScriptedStructuredModel(
        [
            conductor_output("folk_acoustic", vocal=True),
            lyrics_output(),
            melody_output(),
            harmony_output(),
            performance_output(),
            arrangement_output(),
            sound_design_output(),
            mix_review_output(),
            PromptOutput(final_prompt="原声民谣，叙事人声，自然触弦质感。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "写一首讲远行故事的原声民谣"})

    assert result["workflow"] == "folk_acoustic"
    assert PerformanceOutput in llm.calls
    assert RhythmOutput not in llm.calls


def test_hiphop_workflow_builds_beat_before_lyrics_and_flow():
    llm = ScriptedStructuredModel(
        [
            conductor_output("hiphop_vocal", vocal=True),
            rhythm_output(),
            lyrics_output(),
            melody_output(),
            harmony_output(),
            performance_output(),
            arrangement_output(),
            sound_design_output(),
            mix_review_output(),
            PromptOutput(final_prompt="嘻哈人声，boom bap beat，清晰 flow 与 hook。"),
        ]
    )

    result = build_graph(llm).invoke({"user_request": "做一首 boom bap 说唱"})

    assert result["workflow"] == "hiphop_vocal"
    assert llm.calls[:3] == [ConductorOutput, RhythmOutput, LyricsOutput]
    assert result["performance_plan"].humanization


def test_prompt_json_accepts_fenced_json():
    from agents.base import Agent

    agent = Agent(
        name="Prompt Test Agent",
        llm=FencedJsonModel(),
        system_prompt="只返回最终提示词。",
        output_schema=PromptOutput,
        input_fields=("user_request",),
    )

    result = agent({"user_request": "写一首民谣"})

    assert result["final_prompt"].startswith("温暖民谣")


def test_json_mode_uses_plain_chat_for_compatibility(monkeypatch):
    from agents.base import Agent

    monkeypatch.setenv("LLM_STRUCTURED_OUTPUT_METHOD", "json_mode")
    model = FencedJsonModel()
    agent = Agent(
        name="Prompt Test Agent",
        llm=model,
        system_prompt="只返回最终提示词。",
        output_schema=PromptOutput,
        input_fields=("user_request",),
    )

    result = agent({"user_request": "写一首民谣"})

    assert result["final_prompt"].startswith("温暖民谣")


def test_creative_agents_fallback_when_model_returns_empty_response():
    result = build_graph(FailingAfterConductorModel()).invoke(
        {"user_request": "一首旋律轻快的芭乐流行曲"}
    )

    assert result["workflow"] == "pop_vocal"
    assert result["lyrics"].hook
    assert result["melody_plan"].tempo
    assert result["arrangement_plan"].instrumentation
    assert result["final_prompt"]
