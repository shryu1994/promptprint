import math
from collections import Counter, defaultdict
from typing import List

from wami.model import QuestionRecord, record_to_dict
from wami import textutil

LENGTH_BUCKETS = [(0, 60), (60, 200), (200, 600), (600, 10 ** 9)]
LENGTH_LABELS = ["xs", "s", "m", "l"]


def _month(ts: str) -> str:
    return ts[:7] if len(ts) >= 7 else "unknown"


def _hour(ts: str) -> str:
    # ISO: "...T10:00:00+00:00" → "10"
    if "T" in ts and len(ts) >= 13:
        return ts[11:13]
    return "??"


def _length_label(n: int) -> str:
    for (lo, hi), label in zip(LENGTH_BUCKETS, LENGTH_LABELS):
        if lo <= n < hi:
            return label
    return "l"


def _confidence_tier(total: int, active_months: int, max_month_ratio: float) -> tuple[str, str]:
    """데이터 신뢰도 티어를 결정적으로 계산한다.

    Rules (순서 중요 — 먼저 맞는 조건이 우선):
      snapshot: total < 100  OR  active_months < 2  OR  max_month_ratio > 0.7
                → 데이터가 너무 적거나 한 달에 집중됨.
      partial:  total < 500  OR  active_months < 3   OR  max_month_ratio > 0.5
                → 어느 정도 있지만 추세 분석엔 주의 필요.
      full:     그 외.
    """
    if total < 100 or active_months < 2 or max_month_ratio > 0.7:
        return "snapshot", "데이터가 적거나 한 달에 집중되어 신중히 해석 필요"
    if total < 500 or active_months < 3 or max_month_ratio > 0.5:
        return "partial", "데이터가 충분하지 않아 추세 해석 시 주의 권장"
    return "full", "충분히 분산된 데이터로 신뢰도 높음"


def _meta(records: List[QuestionRecord]) -> dict:
    by_tool = Counter(r.tool for r in records)
    ts_sorted = sorted(r.ts for r in records if r.ts)
    date_range = [ts_sorted[0], ts_sorted[-1]] if ts_sorted else [None, None]

    total = len(records)
    by_month = Counter(_month(r.ts) for r in records)
    active_months = len(by_month)
    max_month_count = max(by_month.values(), default=0)
    max_month_ratio = max_month_count / total if total > 0 else 0.0

    tier, note = _confidence_tier(total, active_months, max_month_ratio)

    return {
        "total_questions": total,
        "by_tool": dict(by_tool),
        "date_range": date_range,
        "confidence_tier": tier,
        "confidence_note": note,
    }


def _activity(records: List[QuestionRecord]) -> dict:
    by_month = Counter(_month(r.ts) for r in records)
    by_hour = Counter(_hour(r.ts) for r in records)
    return {
        "by_month": dict(sorted(by_month.items())),
        "by_hour": dict(sorted(by_hour.items())),
    }


def _shape(records: List[QuestionRecord]) -> dict:
    length_buckets = Counter()
    code_block_count = 0
    multistep_count = 0
    len_sum_by_month = defaultdict(int)
    cnt_by_month = defaultdict(int)
    for r in records:
        n = len(r.text)
        length_buckets[_length_label(n)] += 1
        if textutil.has_code_block(r.text):
            code_block_count += 1
        if textutil.is_multistep(r.text):
            multistep_count += 1
        m = _month(r.ts)
        len_sum_by_month[m] += n
        cnt_by_month[m] += 1
    avg_len_by_month = {
        m: round(len_sum_by_month[m] / cnt_by_month[m], 1) for m in sorted(cnt_by_month)
    }
    return {
        "total": len(records),
        "length_buckets": dict(length_buckets),
        "code_block_count": code_block_count,
        "multistep_count": multistep_count,
        "avg_len_by_month": avg_len_by_month,
    }


TOP_TERMS_N = 40


def _topics(records: List[QuestionRecord]) -> dict:
    term_total = Counter()
    term_month = defaultdict(Counter)   # term -> {month: count}
    term_projects = defaultdict(set)    # term -> {project, ...}
    projects = set()
    for r in records:
        m = _month(r.ts)
        if r.project:
            projects.add(r.project)
        seen_in_q = set(textutil.tokens(r.text))  # 질문당 1회만 카운트(빈도 왜곡 방지)
        for t in seen_in_q:
            term_total[t] += 1
            term_month[t][m] += 1
            if r.project:
                term_projects[t].add(r.project)

    num_projects = len(projects)

    def _score(term: str, count: int) -> float:
        # 주제성 가중: 적은 프로젝트에 집중된 term 일수록 가점(빈도 상위 ≠ 주제).
        # 모든 프로젝트에 두루 나오는 보일러플레이트(return/name 등)는 강등된다.
        # 단일 프로젝트(또는 project 정보 없음)면 균일 → 순수 빈도로 폴백.
        pc = len(term_projects[term]) or 1
        spec = math.log(1 + num_projects / pc) if num_projects else 1.0
        return count * spec

    ranked = sorted(
        term_total.items(),
        key=lambda kv: (-_score(kv[0], kv[1]), -kv[1], kv[0]),
    )[:TOP_TERMS_N]
    timeline = {
        term: dict(sorted(term_month[term].items()))
        for term, _ in ranked
    }
    return {
        # [{term, count, project_count}, ...] — project_count 로 주제성 투명 노출
        "top_terms": [
            {"term": t, "count": c, "project_count": len(term_projects[t])}
            for t, c in ranked
        ],
        "term_timeline": timeline,        # {term: {month: count}}
    }


SIGNAL_KEYS = ("critique", "verify", "delegate", "counter")


def _metaskill(records: List[QuestionRecord]) -> dict:
    # 두 지표를 함께 노출한다:
    #  - totals/by_month        : 매치 '횟수' 합 (한 메시지의 다중 매치 포함 — 길이에 민감)
    #  - totals_msgs/by_month_msgs : 신호가 1회+ 등장한 '메시지 수' (0/1 — 길이 강건, 트렌드 1차 지표)
    totals = Counter()
    totals_msgs = Counter()
    by_month = defaultdict(Counter)
    by_month_msgs = defaultdict(Counter)
    for r in records:
        sig = textutil.metaskill_signals(r.text)
        m = _month(r.ts)
        for k in SIGNAL_KEYS:
            v = sig.get(k, 0)
            if v:
                totals[k] += v
                by_month[m][k] += v
                totals_msgs[k] += 1
                by_month_msgs[m][k] += 1
    return {
        "totals": {k: totals.get(k, 0) for k in SIGNAL_KEYS},
        "totals_msgs": {k: totals_msgs.get(k, 0) for k in SIGNAL_KEYS},
        # by_month[month] only contains signal keys that fired (non-zero).
        # Consumers must use .get(key, 0) for missing keys.
        "by_month": {m: dict(c) for m, c in sorted(by_month.items())},
        "by_month_msgs": {m: dict(c) for m, c in sorted(by_month_msgs.items())},
    }


MASTERY_TOP_N = 60
SAMPLES_PER_BUCKET = 3


def _mastery(records: List[QuestionRecord]) -> dict:
    # 주제(term)별 첫/마지막 등장 월과 빈도 → 반복→소멸 분석의 원자료.
    first = {}
    last = {}
    count = Counter()
    for r in records:
        m = _month(r.ts)
        for t in set(textutil.tokens(r.text)):
            count[t] += 1
            if t not in first or m < first[t]:
                first[t] = m
            if t not in last or m > last[t]:
                last[t] = m
    rows = []
    for term, c in sorted(count.items(), key=lambda kv: (-kv[1], kv[0]))[:MASTERY_TOP_N]:
        rows.append({
            "term": term,
            "count": c,
            "first": first[term],
            "last": last[term],
            "active": first[term] != last[term],  # 여러 달에 걸쳐 등장했는가
        })
    return {"topic_lifespan": rows}


def _tool_compare(records: List[QuestionRecord]) -> dict:
    out = {}
    by_tool = defaultdict(list)
    for r in records:
        by_tool[r.tool].append(r)
    for tool, recs in sorted(by_tool.items()):
        lengths = [len(r.text) for r in recs]
        code = sum(1 for r in recs if textutil.has_code_block(r.text))
        out[tool] = {
            "count": len(recs),
            "avg_len": round(sum(lengths) / len(lengths), 1) if lengths else 0,
            "code_block_rate": round(code / len(recs), 3) if recs else 0,
        }
    return out


def _stratified_samples(records: List[QuestionRecord]) -> dict:
    # (month, tool) 버킷별로 등간격 K개를 결정적으로 뽑는다(난수 없음).
    buckets = defaultdict(list)
    for r in records:
        buckets[(_month(r.ts), r.tool)].append(r)
    chosen = []
    for key in sorted(buckets):
        items = sorted(buckets[key], key=lambda r: (r.ts, r.turn_idx, r.text))
        if len(items) <= SAMPLES_PER_BUCKET:
            picks = items
        else:
            step = len(items) / SAMPLES_PER_BUCKET
            idxs = sorted({int(i * step) for i in range(SAMPLES_PER_BUCKET)})
            picks = [items[i] for i in idxs]
        chosen.extend(picks)
    chosen.sort(key=lambda r: (r.ts, r.tool, r.turn_idx))
    return {"stratified": [record_to_dict(r) for r in chosen]}


def build_aggregates(records: List[QuestionRecord]) -> dict:
    """결정적 집계. 8개 섹션을 반환한다."""
    return {
        "meta": _meta(records),
        "activity": _activity(records),
        "shape": _shape(records),
        "topics": _topics(records),
        "metaskill": _metaskill(records),
        "mastery": _mastery(records),
        "tool_compare": _tool_compare(records),
        "samples": _stratified_samples(records),
    }
