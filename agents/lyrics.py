from agents.base import Agent
from langchain_core.language_models.chat_models import BaseChatModel
from lib.prompt import lyrics
from lib.skills import with_skills
from models.state import LyricsDraft, LyricsOutput, State

class LyricsAgent(Agent):
    def __init__(self, llm: BaseChatModel):
        super().__init__(
            name = "作词南郭",
            llm = llm,
            system_prompt=with_skills(lyrics(), "lyrics-reference-audio"),
            output_schema=LyricsOutput,
            input_fields=("user_request", "creative_brief", "instructions_for_agents"),
        )

    def fallback(self, state: State, exc: Exception) -> LyricsOutput:
        brief = state.get("creative_brief")
        theme = getattr(brief, "theme", state.get("user_request", "旅程")) if brief else state.get("user_request", "旅程")
        language = getattr(brief, "language", "中文") if brief else "中文"
        hook = "风会带我到明天"
        return LyricsOutput(
            lyrics=LyricsDraft(
                verse=["轻轻走过旧街边", "把心事交给时间"],
                chorus=[hook, "把微光唱进夜里面"],
                outro=["回声慢慢停歇"],
                language=language,
                theme=theme,
                hook=hook,
                singing_style_hint=getattr(brief, "vocal_style", "自然、轻快") if brief else "自然、轻快",
            )
        )
