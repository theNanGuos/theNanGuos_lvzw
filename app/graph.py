from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from agents.arrange import ArrangeAgent
from agents.conductor import ConductorAgent
from agents.lyrics import LyricsAgent
from agents.melody import MelodyAgent
from agents.prompt_compiler import PromptCompilerAgent
from models.state import State, WorkflowName


def route_workflow(state: State) -> WorkflowName:
    return state["workflow"]


def build_graph(llm: BaseChatModel):
    builder = StateGraph(State)

    builder.add_node("conductor", ConductorAgent(llm))
    builder.add_node("lyrics", LyricsAgent(llm))
    builder.add_node("melody", MelodyAgent(llm))
    builder.add_node("arrange", ArrangeAgent(llm))
    builder.add_node("prompt_compiler", PromptCompilerAgent(llm))

    builder.add_edge(START, "conductor")
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
    builder.add_edge("arrange", "prompt_compiler")
    builder.add_edge("prompt_compiler", END)

    return builder.compile()
