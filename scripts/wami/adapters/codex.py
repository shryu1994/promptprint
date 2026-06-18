import glob
import json
import os
from typing import Iterable, Iterator, List, Optional

from wami.adapters import register
from wami.adapters.base import Adapter
from wami.model import QuestionRecord
from wami import textutil


def _user_text_from_payload(payload: dict) -> Optional[str]:
    """payload에서 사용자가 친 질문 텍스트를 뽑는다. 없으면 None."""
    ptype = payload.get("type")
    # 1) message + role=user 의 input_text 블록
    if ptype == "message" and payload.get("role") == "user":
        content = payload.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                b.get("text")
                for b in content
                if isinstance(b, dict) and b.get("type") == "input_text" and isinstance(b.get("text"), str)
            ]
            if parts:
                return "\n".join(parts)
        return None
    # 2) user_message 이벤트
    if ptype == "user_message":
        msg = payload.get("message")
        if isinstance(msg, str):
            return msg
    return None


@register
class CodexAdapter(Adapter):
    tool = "codex"

    def default_roots(self) -> List[str]:
        base = os.path.expanduser("~/.codex")
        return [
            os.path.realpath(os.path.join(base, "sessions")),
            os.path.realpath(os.path.join(base, "log")),
        ]

    def iter_records(self, roots: Iterable[str]) -> Iterator[QuestionRecord]:
        seen_files = set()
        for root in roots:
            if not root or not os.path.exists(root):
                continue
            if root.endswith(".jsonl") and os.path.isfile(root):
                rp = os.path.realpath(root)
                if rp not in seen_files:
                    seen_files.add(rp)
                    yield from self.iter_records_from_file(root)
            else:
                for path in sorted(glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)):
                    rp = os.path.realpath(path)
                    if rp in seen_files:
                        continue
                    seen_files.add(rp)
                    yield from self.iter_records_from_file(path)

    def iter_records_from_file(self, path: str) -> Iterator[QuestionRecord]:
        # 1st pass: read all lines and resolve session_id / project from session_meta.
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except OSError:
            return

        session_id = os.path.splitext(os.path.basename(path))[0]
        project = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if not isinstance(obj, dict) or obj.get("type") != "session_meta":
                continue
            payload = obj.get("payload")
            if not isinstance(payload, dict):
                continue
            if payload.get("id"):
                session_id = str(payload["id"])
            cwd = payload.get("cwd")
            if isinstance(cwd, str) and cwd:
                project = os.path.basename(cwd)
            break  # only one session_meta expected per file

        # 2nd pass: emit records using the fixed session_id / project.
        turn = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            payload = obj.get("payload")
            if not isinstance(payload, dict):
                continue
            if obj.get("type") == "session_meta":
                continue
            text = _user_text_from_payload(payload)
            if text is None or textutil.is_noise(text):
                continue
            ts = textutil.norm_ts(obj.get("timestamp"))
            yield QuestionRecord(
                ts=ts,
                tool=self.tool,
                session_id=session_id,
                project=project,
                text=text.strip(),
                turn_idx=turn,
            )
            turn += 1
