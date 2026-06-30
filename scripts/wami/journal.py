"""체크 저널 — check가 자기 과거를 기억하게 하는 로컬 상태(복리 점검 루프).

매 check마다 *길이-강건 비율 + 반복 노역 후보(라벨·측정값)*만 append-only로 적고,
다음 check가 직전 항목과 비교해 '지난 점검 이후 움직임 + 노역이 줄었나'를 낸다.
원문 질문 0(비율·term 라벨만) · stdlib · 무네트워크. 저널은 `*.local.*`로 gitignored."""
import json
import os
from typing import List, Optional


def read_journal(path: str) -> List[dict]:
    """저널을 읽어 항목 리스트 반환. 없거나 깨졌으면 [](graceful, delta 빈처리와 동일 정신)."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def previous_entry(journal: List[dict], current_as_of: str) -> Optional[dict]:
    """current_as_of 보다 *엄격히 이전*인 가장 최근 항목(같은 날 재실행의 자기비교 방지)."""
    earlier = [e for e in journal if e.get("as_of") and e["as_of"] < current_as_of]
    return max(earlier, key=lambda e: e["as_of"]) if earlier else None


def upsert_journal(path: str, entry: dict) -> None:
    """같은 as_of 항목은 교체(재실행 중복 방지) 후 as_of 순 정렬해 저장."""
    journal = [e for e in read_journal(path) if e.get("as_of") != entry.get("as_of")]
    journal.append(entry)
    journal.sort(key=lambda e: e.get("as_of") or "")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(journal, fh, ensure_ascii=False, indent=2)


def journal_entry(delta: dict) -> dict:
    """build_delta 결과에서 *프라이버시 안전*한 항목만 뽑는다(원문 0, 비율·라벨만)."""
    rec = delta["recent"]
    return {
        "as_of": delta["as_of"],
        "window_days": delta["window_days"],
        "metrics": {
            "metaskill_rate": dict(rec["metaskill_rate"]),  # {signal_key: float} — 신호 라벨→비율, 원문 없음
            "one_shot_rate": rec["one_shot_rate"],
            "code_block_rate": rec["code_block_rate"],
            "q_per_session": rec["q_per_session"],
            "multistep_rate": rec["multistep_rate"],
            "avg_len": rec["avg_len"],
        },
        "skill_candidates": [
            {"term": c["term"], "recent_count": c["recent_count"], "avg_len": c["avg_len"]}
            for c in delta.get("skill_candidates", [])
        ],
    }
