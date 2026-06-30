"""Jan (로컬 LLM 데스크톱) 어댑터.

Jan은 스레드별로 `threads/<thread_id>/messages.jsonl`(줄당 메시지 JSON)을 남긴다.
사용자 메시지(role=="user")의 텍스트만 QuestionRecord로 추출한다.
포맷: {"role":"user","content":[{"type":"text","text":{"value":"..."}}],"created_at":<unix>}
(created_at은 초 또는 밀리초 — 자릿수로 판별해 ISO로 변환.)
"""
import glob
import json
import os
from datetime import datetime, timezone
from typing import Iterable, Iterator, List, Optional

from wami.adapters import register
from wami.adapters.base import Adapter
from wami.model import QuestionRecord
from wami import textutil


def _epoch_to_iso(v) -> str:
    """unix 초/밀리초 → ISO-8601 UTC. 13자리(>=1e12)면 ms로 본다. 실패 시 ''."""
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return ""
    secs = v / 1000.0 if v >= 1e12 else float(v)
    try:
        return datetime.fromtimestamp(secs, tz=timezone.utc).isoformat()
    except (ValueError, OSError, OverflowError):
        return ""


def _user_text(content) -> Optional[str]:
    """content(문자열 또는 [{type,text:{value}}] 리스트)에서 사용자 텍스트를 뽑는다."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                continue
            t = block.get("text")
            if isinstance(t, dict) and isinstance(t.get("value"), str):
                parts.append(t["value"])
            elif isinstance(t, str):
                parts.append(t)
        if parts:
            return "\n".join(parts)
    return None


@register
class JanAdapter(Adapter):
    tool = "jan"

    def default_roots(self) -> List[str]:
        home = os.path.expanduser("~")
        bases = [
            os.path.join(home, "Library", "Application Support", "Jan"),  # macOS
            os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share"), "Jan"),  # Linux
        ]
        appdata = os.environ.get("APPDATA")
        if appdata:
            bases.append(os.path.join(appdata, "Jan"))  # Windows
        roots = []
        for base in bases:
            roots.append(os.path.join(base, "data", "threads"))  # 현재 레이아웃
            roots.append(os.path.join(base, "threads"))           # 레거시 레이아웃
        return roots

    def iter_records(self, roots: Iterable[str]) -> Iterator[QuestionRecord]:
        for root in roots:
            if not root:
                continue
            if root.endswith(".jsonl") and os.path.isfile(root):
                yield from self._from_file(root, os.path.basename(os.path.dirname(root)))
            elif os.path.isdir(root):
                for path in sorted(glob.glob(os.path.join(root, "*", "messages.jsonl"))):
                    yield from self._from_file(path, os.path.basename(os.path.dirname(path)))

    def _from_file(self, path: str, thread_id: str) -> Iterator[QuestionRecord]:
        try:
            fh = open(path, "r", encoding="utf-8")
        except OSError:
            return
        turn = 0
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(obj, dict) or obj.get("role") != "user":
                    continue
                text = _user_text(obj.get("content"))
                if not text:
                    continue
                self.stats["scanned"] += 1
                if textutil.is_noise(text):
                    self.stats["dropped_noise"] += 1
                    continue
                self.stats["kept"] += 1
                yield QuestionRecord(
                    ts=_epoch_to_iso(obj.get("created_at")),
                    tool=self.tool,
                    session_id=thread_id or os.path.basename(path),
                    project=None,
                    text=text.strip(),
                    turn_idx=turn,
                )
                turn += 1
