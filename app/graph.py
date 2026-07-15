from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from agents.arrange import ArrangeAgent
from agents.audio_reference import AudioReferenceAgent
from agents.conductor import ConductorAgent
from agents.harmony import HarmonyAgent
from agents.lyrics import LyricsAgent
from agents.melody import MelodyAgent
from agents.mix_review import MixReviewAgent
from agents.prompt_compiler import PromptCompilerAgent
from agents.rhythm import RhythmAgent
from agents.sound_design import SoundDesignAgent
from lib.score import export_score_node
from models.state import State, WorkflowName


def route_workflow(state: State) -> WorkflowName:
    return state["workflow"]


def route_score_export(state: State) -> str:
    if state.get("score_spec") is not None and state.get("artifact_dir"):
        return "score_export"
    return "sound_design"


def route_after_harmony(state: State) -> str:
    if state["workflow"] in {"classical_instrumental", "electronic_instrumental", "soundtrack_score"}:
        return "arrange"
    return "rhythm"


def route_after_rhythm(state: State) -> str:
    if state["workflow"] == "electronic_instrumental":
        return "melody"
    return "arrange"


def route_after_arrange(state: State) -> str:
    if state["workflow"] == "classical_instrumental":
        return route_score_export(state)
    return "sound_design"


def build_graph(llm: BaseChatModel):
    builder = StateGraph(State)

    builder.add_node("audio_reference", AudioReferenceAgent(llm))
    builder.add_node("conductor", ConductorAgent(llm))
    builder.add_node("lyrics", LyricsAgent(llm))
    builder.add_node("melody", MelodyAgent(llm))
    builder.add_node("harmony", HarmonyAgent(llm))
    builder.add_node("rhythm", RhythmAgent(llm))
    builder.add_node("arrange", ArrangeAgent(llm))
    builder.add_node("sound_design", SoundDesignAgent(llm))
    builder.add_node("mix_review", MixReviewAgent(llm))
    builder.add_node("score_export", export_score_node)
    builder.add_node("prompt_compiler", PromptCompilerAgent(llm))

    builder.add_edge(START, "audio_reference")
    builder.add_edge("audio_reference", "conductor")
    builder.add_conditional_edges(
        "conductor",
        route_workflow,
        {
            "pop_vocal": "lyrics",
            "classical_instrumental": "melody",
            "electronic_instrumental": "rhythm",
            "soundtrack_score": "melody",
        },
    )
    builder.add_edge("lyrics", "melody")
    builder.add_edge("melody", "harmony")
    builder.add_conditional_edges(
        "harmony",
        route_after_harmony,
        {
            "rhythm": "rhythm",
            "arrange": "arrange",
        },
    )
    builder.add_conditional_edges(
        "rhythm",
        route_after_rhythm,
        {
            "melody": "melody",
            "arrange": "arrange",
        },
    )
    builder.add_conditional_edges(
        "arrange",
        route_after_arrange,
        {
            "score_export": "score_export",
            "sound_design": "sound_design",
        },
    )
    builder.add_edge("score_export", "sound_design")
    builder.add_edge("sound_design", "mix_review")
    builder.add_edge("mix_review", "prompt_compiler")
    builder.add_edge("prompt_compiler", END)

    return builder.compile()
