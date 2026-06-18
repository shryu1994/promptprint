from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class QuestionRecord:
    ts: str            # ISO-8601 UTC, e.g. "2026-01-02T03:04:05+00:00"
    tool: str          # "claude" | "codex"
    session_id: str
    project: Optional[str]
    text: str
    turn_idx: int


def record_to_dict(r: QuestionRecord) -> dict:
    return asdict(r)


def record_from_dict(d: dict) -> QuestionRecord:
    return QuestionRecord(
        ts=d["ts"],
        tool=d["tool"],
        session_id=d["session_id"],
        project=d.get("project"),
        text=d["text"],
        turn_idx=int(d["turn_idx"]),
    )
