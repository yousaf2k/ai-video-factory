"""
Agent conversation persistence.

Each conversation is a JSON file under output/agent/conversations/ holding the
full message history including tool calls and tool results, so the UI can
render a transparent audit trail of everything the agent did.
"""
import os
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import config
from core.json_atomic import atomic_write_json, read_json


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ConversationStore:
    def __init__(self, directory: Optional[str] = None):
        self.directory = directory or os.path.join(config.AGENT_DATA_DIR, "conversations")
        self._lock = threading.RLock()

    def _path(self, conversation_id: str) -> str:
        return os.path.join(self.directory, f"{conversation_id}.json")

    # ------------------------------------------------------------------ CRUD
    def create(self, project_id: Optional[str] = None, title: Optional[str] = None) -> Dict:
        conversation = {
            "id": f"conv_{uuid.uuid4().hex[:12]}",
            "title": title or "New chat",
            "project_id": project_id,
            "created_at": _now(),
            "updated_at": _now(),
            "messages": [],
        }
        with self._lock:
            os.makedirs(self.directory, exist_ok=True)
            atomic_write_json(self._path(conversation["id"]), conversation, indent=2)
        return conversation

    def list_conversations(self) -> List[Dict]:
        with self._lock:
            items: List[Dict] = []
            if not os.path.isdir(self.directory):
                return items
            for fname in os.listdir(self.directory):
                if not fname.endswith(".json"):
                    continue
                data = read_json(self._path(fname[:-5]), default=None)
                if not isinstance(data, dict):
                    continue
                items.append({
                    "id": data.get("id", fname[:-5]),
                    "title": data.get("title", "Untitled"),
                    "project_id": data.get("project_id"),
                    "updated_at": data.get("updated_at", ""),
                    "message_count": len(data.get("messages", [])),
                })
            items.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
            return items

    def get(self, conversation_id: str) -> Optional[Dict]:
        with self._lock:
            data = read_json(self._path(conversation_id), default=None)
            if not isinstance(data, dict):
                return None
            data.setdefault("id", conversation_id)
            data.setdefault("messages", [])
            return data

    def append_messages(self, conversation_id: str, messages: List[Dict]) -> Dict:
        with self._lock:
            conversation = self.get(conversation_id)
            if conversation is None:
                raise ValueError(f"Conversation '{conversation_id}' not found")
            conversation["messages"].extend(messages)
            conversation["updated_at"] = _now()
            # Auto-title from the first user message.
            if conversation.get("title") in (None, "", "New chat"):
                for msg in conversation["messages"]:
                    if msg.get("role") == "user" and msg.get("content"):
                        text = str(msg["content"]).strip().replace("\n", " ")
                        conversation["title"] = text[:60] + ("…" if len(text) > 60 else "")
                        break
            atomic_write_json(self._path(conversation_id), conversation, indent=2)
            return conversation

    def update(self, conversation_id: str, title: Optional[str] = None,
               project_id: Optional[str] = None,
               context_usage: Optional[Dict] = None) -> Dict:
        with self._lock:
            conversation = self.get(conversation_id)
            if conversation is None:
                raise ValueError(f"Conversation '{conversation_id}' not found")
            if title is not None:
                conversation["title"] = title
            if project_id is not None:
                conversation["project_id"] = project_id or None
            if context_usage is not None:
                conversation["context_usage"] = context_usage
            conversation["updated_at"] = _now()
            atomic_write_json(self._path(conversation_id), conversation, indent=2)
            return conversation

    def delete(self, conversation_id: str) -> bool:
        with self._lock:
            path = self._path(conversation_id)
            if os.path.isfile(path):
                os.remove(path)
                return True
            return False


_store: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
