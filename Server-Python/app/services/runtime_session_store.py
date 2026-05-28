from collections import deque
from threading import Lock

from app.contracts.runtime_behavior import RuntimeConversationTurn


class RuntimeSessionStore:
    def __init__(self, max_turns_per_session: int = 40) -> None:
        self._max_turns_per_session = max_turns_per_session
        self._turns_by_session: dict[str, deque[RuntimeConversationTurn]] = {}
        self._lock = Lock()

    def get_recent_turns(self, session_id: str) -> list[RuntimeConversationTurn]:
        with self._lock:
            turns = self._turns_by_session.get(session_id)
            if not turns:
                return []
            return list(turns)

    def append_exchange(self, session_id: str, user_message: str, assistant_reply: str) -> None:
        with self._lock:
            turns = self._turns_by_session.setdefault(
                session_id,
                deque(maxlen=self._max_turns_per_session),
            )
            turns.append(RuntimeConversationTurn(role="user", content=user_message))
            turns.append(RuntimeConversationTurn(role="assistant", content=assistant_reply))

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._turns_by_session.pop(session_id, None)
