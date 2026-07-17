from agents.arrange import ArrangeAgent
from agents.chat import ChatAgent
from agents.conductor import ConductorAgent
from agents.harmony import HarmonyAgent
from agents.improvisation import ImprovisationAgent
from agents.lyrics import LyricsAgent
from agents.melody import MelodyAgent
from agents.mix_review import MixReviewAgent
from agents.performance import PerformanceAgent
from agents.prompt_compiler import PromptCompilerAgent
from agents.rhythm import RhythmAgent
from agents.sound_design import SoundDesignAgent
from lib.skills import read_skill, with_skills


def test_read_skill_strips_frontmatter():
    content = read_skill("suno-prompt-tool-handoff")

    assert content.startswith("# Suno Prompt Tool Handoff")
    assert "description:" not in content.splitlines()[0]
    assert "tools.audio.summarize_generated_audio" in content


def test_read_skill_rejects_path_traversal():
    try:
        read_skill("../AGENTS")
    except ValueError as exc:
        assert "Invalid skill name" in str(exc)
    else:
        raise AssertionError("read_skill accepted path traversal")


def test_with_skills_appends_named_sections():
    prompt = with_skills("base prompt", "lyrics-reference-audio")

    assert prompt.startswith("base prompt")
    assert "## Skill: lyrics-reference-audio" in prompt
    assert "tools.audio.inspect_audio" in prompt


def test_agents_load_role_specific_skills():
    llm = object()

    assert "conductor-tool-routing" in ConductorAgent(llm).system_prompt
    assert "lyrics-reference-audio" in LyricsAgent(llm).system_prompt
    assert "melody-demo-audio" in MelodyAgent(llm).system_prompt
    assert "arrangement-audio-analysis" in ArrangeAgent(llm).system_prompt
    assert "suno-prompt-tool-handoff" in PromptCompilerAgent(llm).system_prompt
    assert "lyrics-reference-audio" not in ArrangeAgent(llm).system_prompt


def test_creative_agents_use_nanguo_role_names():
    llm = object()
    agents = [
        (ConductorAgent(llm), "指挥南郭"),
        (LyricsAgent(llm), "作词南郭"),
        (MelodyAgent(llm), "旋律南郭"),
        (HarmonyAgent(llm), "和声南郭"),
        (RhythmAgent(llm), "节奏南郭"),
        (ImprovisationAgent(llm), "即兴南郭"),
        (PerformanceAgent(llm), "演奏南郭"),
        (ArrangeAgent(llm), "编曲南郭"),
        (SoundDesignAgent(llm), "音色南郭"),
        (MixReviewAgent(llm), "审听南郭"),
        (PromptCompilerAgent(llm), "提示词南郭"),
    ]

    for agent, expected_name in agents:
        assert agent.name == expected_name
        assert agent.system_prompt.startswith(f"# {expected_name}")


def test_chat_agent_uses_nanguo_identity_prompt():
    agent = ChatAgent(object())

    assert agent.name == "对话南郭"
    assert "你是“对话南郭”" in agent.system_prompt
    assert "南郭乐团的对外代表" in agent.system_prompt
    assert "不要自称 Chat Agent" in agent.system_prompt
    assert "previous_works" in agent.system_prompt
