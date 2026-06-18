"""insights.json 구조 검증 (결정적, LLM 호출 없음)."""
from typing import List

DIMENSION_KEYS = (
    "topic_evolution",
    "depth",
    "metaskill",
    "craft",
    "mastery",
    "clusters",
)
CARDS_MIN = 3
CARDS_MAX = 5
BEARINGS_MIN = 2
BEARINGS_MAX = 4


def _nonempty_str(v) -> bool:
    return isinstance(v, str) and v.strip() != ""


def validate_insights(obj) -> List[str]:
    """insights 객체를 검증한다. 위반 메시지 리스트를 반환(빈 리스트면 valid)."""
    errors: List[str] = []
    if not isinstance(obj, dict):
        return ["root: dict가 아님"]

    if obj.get("schema_version") != "1":
        errors.append('schema_version: "1"이어야 함')
    for key in ("headline", "summary"):
        if not _nonempty_str(obj.get(key)):
            errors.append(f"{key}: 비어있지 않은 문자열이어야 함")

    dims = obj.get("dimensions")
    if not isinstance(dims, dict):
        errors.append("dimensions: dict가 아님")
    else:
        for k in DIMENSION_KEYS:
            if k not in dims:
                errors.append(f"dimensions.{k}: 누락됨")
                continue
            d = dims[k]
            if not isinstance(d, dict):
                errors.append(f"dimensions.{k}: dict가 아님")
                continue
            if not _nonempty_str(d.get("narrative")):
                errors.append(f"dimensions.{k}.narrative: 비어있지 않은 문자열이어야 함")
            ev = d.get("evidence")
            if not (isinstance(ev, list) and len(ev) >= 1 and all(_nonempty_str(x) for x in ev)):
                errors.append(f"dimensions.{k}.evidence: 1개 이상의 비어있지 않은 문자열이어야 함")
        extra = set(dims) - set(DIMENSION_KEYS)
        if extra:
            errors.append(f"dimensions: 알 수 없는 키 {sorted(extra)}")

    chapters = obj.get("chapters")
    if not (isinstance(chapters, list) and len(chapters) >= 1):
        errors.append("chapters: 1개 이상의 항목이어야 함")
    else:
        for i, c in enumerate(chapters):
            if not isinstance(c, dict):
                errors.append(f"chapters[{i}]: dict가 아님")
                continue
            for f in ("title", "period", "narrative"):
                if not _nonempty_str(c.get(f)):
                    errors.append(f"chapters[{i}].{f}: 비어있지 않은 문자열이어야 함")

    cards = obj.get("cards")
    if not isinstance(cards, list):
        errors.append("cards: list가 아님")
    elif not (CARDS_MIN <= len(cards) <= CARDS_MAX):
        errors.append(f"cards: {CARDS_MIN}~{CARDS_MAX}개여야 함(현재 {len(cards)})")
    else:
        for i, c in enumerate(cards):
            if not isinstance(c, dict):
                errors.append(f"cards[{i}]: dict가 아님")
                continue
            for f in ("headline", "stat", "caption"):
                if not _nonempty_str(c.get(f)):
                    errors.append(f"cards[{i}].{f}: 비어있지 않은 문자열이어야 함")

    bearings = obj.get("next_bearings")
    if not isinstance(bearings, list):
        errors.append("next_bearings: list가 아님")
    elif not (BEARINGS_MIN <= len(bearings) <= BEARINGS_MAX):
        errors.append(f"next_bearings: {BEARINGS_MIN}~{BEARINGS_MAX}개여야 함(현재 {len(bearings)})")
    else:
        for i, b in enumerate(bearings):
            if not isinstance(b, dict):
                errors.append(f"next_bearings[{i}]: dict가 아님")
                continue
            for f in ("title", "why", "how"):
                if not _nonempty_str(b.get(f)):
                    errors.append(f"next_bearings[{i}].{f}: 비어있지 않은 문자열이어야 함")

    return errors
