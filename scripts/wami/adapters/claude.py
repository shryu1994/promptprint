import glob
import json
import os
from typing import Iterable, Iterator, List

from wami.adapters import register
from wami.adapters.base import Adapter
from wami.model import QuestionRecord
from wami import textutil


def _texts_from_message(message) -> List[str]:
    """user 메시지에서 사용자가 친 텍스트만 추출(tool_result 등 제외)."""
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [content]
    out = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                t = block.get("text")
                if isinstance(t, str):
                    out.append(t)
    return out


@register
class ClaudeAdapter(Adapter):
    tool = "claude"

    def default_roots(self) -> List[str]:
        return [os.path.expanduser("~/.claude/projects")]

    def iter_records(self, roots: Iterable[str]) -> Iterator[QuestionRecord]:
        for root in roots:
            if root.endswith(".jsonl") and os.path.isfile(root):
                yield from self.iter_records_from_file(root)
            else:
                if not root or not os.path.exists(root):
                    continue
                for path in sorted(glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)):
                    yield from self.iter_records_from_file(path)

    def iter_records_from_file(self, path: str) -> Iterator[QuestionRecord]:
        # 세션별 질문 순번을 매긴다.
        turn_by_session = {}
        try:
            fh = open(path, "r", encoding="utf-8")
        except OSError:
            return
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(obj, dict) or obj.get("type") != "user":
                    continue
                texts = _texts_from_message(obj.get("message"))
                if not texts:
                    continue
                self.stats["scanned"] += len(texts)
                # 구조적 제외: 서브에이전트·워크플로 턴은 사람이 친 질문이 아니다.
                # 모든 Claude Code 로그에 있는 표식이라 접두사 denylist보다 견고하다.
                if obj.get("isSidechain") is True or obj.get("agentId"):
                    self.stats["dropped_subagent"] += len(texts)
                    continue
                session_id = obj.get("sessionId") or os.path.basename(path)
                cwd = obj.get("cwd")
                project = os.path.basename(cwd) if isinstance(cwd, str) and cwd else None
                ts = textutil.norm_ts(obj.get("timestamp"))
                for text in texts:
                    if textutil.is_noise(text):
                        self.stats["dropped_noise"] += 1
                        continue
                    self.stats["kept"] += 1
                    idx = turn_by_session.get(session_id, 0)
                    turn_by_session[session_id] = idx + 1
                    yield QuestionRecord(
                        ts=ts,
                        tool=self.tool,
                        session_id=session_id,
                        project=project,
                        text=text.strip(),
                        turn_idx=idx,
                    )
