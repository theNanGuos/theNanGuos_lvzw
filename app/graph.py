from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from agents.arrange import ArrangeAgent
from agents.audio_reference import AudioReferenceAgent
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
    if state["workflow"] in {"folk_acoustic", "hiphop_vocal"}:
        return "performance"
    return "rhythm"


def route_after_rhythm(state: State) -> str:
    if state["workflow"] in {"electronic_instrumental", "jazz_ensemble"}:
        return "melody"
    if state["workflow"] == "hiphop_vocal":
        return "lyrics"
    if state["workflow"] == "rock_vocal":
        return "performance"
    return "arrange"


def route_after_melody(state: State) -> str:
    if state["workflow"] == "jazz_ensemble":
        return "improvisation"
    return "harmony"


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
    builder.add_node("improvisation", ImprovisationAgent(llm))
    builder.add_node("performance", PerformanceAgent(llm))
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
            "jazz_ensemble": "harmony",
            "rock_vocal": "lyrics",
            "folk_acoustic": "lyrics",
            "hiphop_vocal": "rhythm",
        },
    )
    builder.add_edge("lyrics", "melody")
    builder.add_conditional_edges(
        "melody",
        route_after_melody,
        {
            "harmony": "harmony",
            "improvisation": "improvisation",
        },
    )
    builder.add_conditional_edges(
        "harmony",
        route_after_harmony,
        {
            "rhythm": "rhythm",
            "arrange": "arrange",
            "performance": "performance",
        },
    )
    builder.add_conditional_edges(
        "rhythm",
        route_after_rhythm,
        {
            "melody": "melody",
            "lyrics": "lyrics",
            "performance": "performance",
            "arrange": "arrange",
        },
    )
    builder.add_edge("improvisation", "performance")
    builder.add_edge("performance", "arrange")
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
