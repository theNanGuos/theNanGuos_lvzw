from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from agents.arrange import ArrangeAgent
from agents.audio_reference import AudioReferenceAgent
from agents.conductor import ConductorAgent
from agents.lyrics import LyricsAgent
from agents.melody import MelodyAgent
from agents.prompt_compiler import PromptCompilerAgent
from lib.score import export_score_node
from models.state import State, WorkflowName


def route_workflow(state: State) -> WorkflowName:
    return state["workflow"]


def route_score_export(state: State) -> str:
    if state.get("score_spec") is not None and state.get("artifact_dir"):
        return "score_export"
    return "prompt_compiler"


def build_graph(llm: BaseChatModel):
    builder = StateGraph(State)

    builder.add_node("audio_reference", AudioReferenceAgent(llm))
    builder.add_node("conductor", ConductorAgent(llm))
    builder.add_node("lyrics", LyricsAgent(llm))
    builder.add_node("melody", MelodyAgent(llm))
    builder.add_node("arrange", ArrangeAgent(llm))
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
        },
    )
    builder.add_edge("lyrics", "melody")
    builder.add_edge("melody", "arrange")
    builder.add_conditional_edges(
        "arrange",
        route_score_export,
        {
            "score_export": "score_export",
            "prompt_compiler": "prompt_compiler",
        },
    )
    builder.add_edge("score_export", "prompt_compiler")
    builder.add_edge("prompt_compiler", END)

    return builder.compile()
