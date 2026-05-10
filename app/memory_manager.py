"""Conversation persistence in history.json (not committed)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _log_memory(message: str) -> None:
    print(f"[Memory] {message}")


@dataclass
class MemoryManager:
    path: Path
    messages: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> MemoryManager:
        p = Path(path)
        if not p.exists():
            mgr = cls(path=p, messages=[])
            _log_memory(f"history.json not found at {p}; starting empty")
            return mgr
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            _log_memory(f"Could not read history ({e}); starting empty")
            return cls(path=p, messages=[])
        if not isinstance(raw, list):
            _log_memory("Invalid history format; starting empty")
            return cls(path=p, messages=[])
        _log_memory("history.json loaded")
        return cls(path=p, messages=raw)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.messages, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _log_memory("history.json saved")

    def reset(self) -> None:
        self.messages = []
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError:
                pass
        _log_memory("history.json reset")

    def append_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def append_assistant(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": text})

    def snippet_for_prompt(self, max_messages: int = 8, max_chars: int = 2000) -> str:
        if not self.messages:
            return ""
        tail = self.messages[-max_messages:]
        lines: list[str] = []
        for m in tail:
            role = m.get("role", "")
            content = m.get("content", "")
            if isinstance(content, list):
                content = json.dumps(content, ensure_ascii=False)
            lines.append(f"{role}: {content}")
        text = "\n".join(lines)
        if len(text) > max_chars:
            return text[-max_chars:]
        return text
