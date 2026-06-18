from typing import Dict, List, Optional

from wami.adapters import ADAPTERS
# 어댑터 등록을 위해 모듈을 import (side-effect로 register 호출).
from wami.adapters import claude as _claude  # noqa: F401
from wami.adapters import codex as _codex    # noqa: F401
from wami.model import QuestionRecord


def extract_records(roots_by_tool: Optional[Dict[str, List[str]]] = None) -> List[QuestionRecord]:
    """
    roots_by_tool: {tool_name: [경로...]} 또는 None(=각 어댑터의 기본 경로).
    반환: ts 오름차순으로 정렬된 QuestionRecord 리스트(중복 제거).
    """
    records: List[QuestionRecord] = []
    for tool, adapter_cls in sorted(ADAPTERS.items()):
        adapter = adapter_cls()
        if roots_by_tool is None:
            roots = adapter.default_roots()
        elif tool in roots_by_tool:
            roots = roots_by_tool[tool]
        else:
            continue
        records.extend(adapter.iter_records(roots))

    # 중복 제거: (tool, session, ts, text) 동일하면 같은 레코드로 본다.
    seen = set()
    deduped = []
    for r in records:
        key = (r.tool, r.session_id, r.ts, r.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    # ts(문자열 ISO는 사전식=시간순) → tool → session 안정 정렬.
    deduped.sort(key=lambda r: (r.ts, r.tool, r.session_id, r.turn_idx))
    return deduped
