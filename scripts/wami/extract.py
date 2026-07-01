from collections import Counter
from typing import Dict, List, Optional

from wami.adapters import ADAPTERS
# 어댑터 등록을 위해 모듈을 import (side-effect로 register 호출).
from wami.adapters import claude as _claude  # noqa: F401
from wami.adapters import codex as _codex    # noqa: F401
from wami.adapters import jan as _jan        # noqa: F401
from wami.model import QuestionRecord

# 프로그램적 중복 판정: 긴 동일 텍스트가 여러 세션에 반복되면 사람 질문이 아니라
# eval 하네스·RAG 에이전트·배치 작업이 같은 프롬프트를 반복한 것으로 본다.
# 짧은 반복("continue"·"1"·"진행해" 등 사람 넛지)은 보존하려고 길이 하한을 둔다.
DUP_MIN_LEN = 280     # 이 길이 이상이고
DUP_MIN_COUNT = 5     # 이 횟수 이상 똑같이 반복되면 제거

# 초대형 블록: 사람이 한 번에 타이핑하지 않는 길이(코드리뷰·시큐리티리뷰가 레포
# 전체 diff 를 쏟아낸 툴 덤프 등). p99 가 ~6만자, 이 덤프는 40만자+ — 사람 질문이
# 아니라 잔여 기계 트래픽이라 후보·통계를 오염시킨다(흔한 단어 count 폭증). 제거한다.
OVERSIZE_LEN = 50000


def _drop_oversized(records: List[QuestionRecord], scan: Counter) -> List[QuestionRecord]:
    """OVERSIZE_LEN 초과 블록(툴 덤프)을 제거하고 제거 수를 scan 에 기록한다."""
    kept = [r for r in records if len(r.text) <= OVERSIZE_LEN]
    scan["dropped_oversized"] += len(records) - len(kept)
    return kept


def _collapse_programmatic(records: List[QuestionRecord],
                           stats: Optional[Counter] = None) -> List[QuestionRecord]:
    """긴 동일 텍스트의 고빈도 반복(프로그램적 트래픽)을 제거한다.

    접두사 denylist로는 못 잡는 잔여 기계 트래픽(매 호출 같은 페르소나 프롬프트)을
    구조적으로 거른다 — 새 에이전트가 생겨도 '동일 텍스트 N회+'면 잡힌다."""
    text_counts = Counter(r.text for r in records)
    out = []
    dropped = 0
    for r in records:
        if len(r.text) >= DUP_MIN_LEN and text_counts[r.text] >= DUP_MIN_COUNT:
            dropped += 1
            continue
        out.append(r)
    if stats is not None:
        stats["dropped_duplicate"] += dropped
    return out


def extract_records(roots_by_tool: Optional[Dict[str, List[str]]] = None,
                    stats_out: Optional[Counter] = None) -> List[QuestionRecord]:
    """
    roots_by_tool: {tool_name: [경로...]} 또는 None(=각 어댑터의 기본 경로).
    stats_out:     주어지면 신뢰 영수증(scanned/dropped_*/kept)을 채운다.
    반환: ts 오름차순으로 정렬된 QuestionRecord 리스트(중복·프로그램적 트래픽 제거).
    """
    records: List[QuestionRecord] = []
    scan = Counter()
    for tool, adapter_cls in sorted(ADAPTERS.items()):
        adapter = adapter_cls()
        if roots_by_tool is None:
            roots = adapter.default_roots()
        elif tool in roots_by_tool:
            roots = roots_by_tool[tool]
        else:
            continue
        records.extend(adapter.iter_records(roots))
        scan.update(adapter.stats)

    # 중복 제거: (tool, session, ts, text) 동일하면 같은 레코드로 본다.
    seen = set()
    deduped = []
    for r in records:
        key = (r.tool, r.session_id, r.ts, r.text)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    scan["dropped_dedup"] += len(records) - len(deduped)

    # 프로그램적 트래픽(긴 동일 텍스트 고빈도 반복) 제거.
    deduped = _collapse_programmatic(deduped, scan)

    # 초대형 툴 덤프(코드리뷰·시큐리티리뷰 등 레포 전체 diff) 제거 — 잔여 기계 트래픽.
    deduped = _drop_oversized(deduped, scan)

    # 어댑터의 잠정 kept를 최종 kept로 덮어쓴다(dedup·중복제거 반영).
    scan["kept"] = len(deduped)
    if stats_out is not None:
        stats_out.clear()
        stats_out.update(scan)

    # ts(문자열 ISO는 사전식=시간순) → tool → session 안정 정렬.
    deduped.sort(key=lambda r: (r.ts, r.tool, r.session_id, r.turn_idx))
    return deduped
