from pathlib import Path
from threading import RLock

from models.chat import ChatMessage, ChatSession, ChatSessionCreate
from models.project import utc_now


class SessionNotFoundError(FileNotFoundError):
    pass


class LocalSessionStore:
    def __init__(self, root: Path | str = "data/sessions"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def list_sessions(self) -> list[ChatSession]:
        sessions = [
            ChatSession.model_validate_json(path.read_text(encoding="utf-8"))
            for path in self.root.glob("*/session.json")
        ]
        return sorted(sessions, key=lambda session: session.updated_at, reverse=True)

    def create_session(self, data: ChatSessionCreate) -> ChatSession:
        session = ChatSession(title=data.title)
        self.save_session(session)
        return session

    def get_session(self, session_id: str) -> ChatSession:
        path = self._session_path(session_id)
        if not path.is_file():
            raise SessionNotFoundError(session_id)
        return ChatSession.model_validate_json(path.read_text(encoding="utf-8"))

    def save_session(self, session: ChatSession) -> None:
        session.updated_at = utc_now()
        path = self._session_path(session.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        with self._lock:
            temporary.write_text(session.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(path)

    def add_message(self, session_id: str, message: ChatMessage) -> ChatSession:
        session = self.get_session(session_id)
        session.messages.append(message)
        self.save_session(session)
        return session

    def _session_path(self, session_id: str) -> Path:
        if not session_id.isalnum():
            raise SessionNotFoundError(session_id)
        return self.root / session_id / "session.json"
