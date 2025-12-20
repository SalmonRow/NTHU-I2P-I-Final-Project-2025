import threading
import time
from dataclasses import dataclass, asdict
from typing import List, Dict

@dataclass
class ChatMessage:
    idx: int
    sender_id: int
    content: str
    timestamp: float

class ChatHandler:
    _lock: threading.Lock
    _messages: List[ChatMessage]
    _next_idx: int
    MAX_HISTORY = 50

    def __init__(self):
        self._lock = threading.Lock()
        self._messages = []
        self._next_idx = 0

    def add_message(self, sender_id: int, content: str) -> None:
        with self._lock:
            msg = ChatMessage(self._next_idx, sender_id, content, time.time())
            self._messages.append(msg)
            self._next_idx += 1
            if len(self._messages) > self.MAX_HISTORY:
                self._messages.pop(0)

    def get_messages(self, after_idx: int = -1) -> List[dict]:
        with self._lock:
            # Return new messages
            return [asdict(m) for m in self._messages if m.idx > after_idx]
