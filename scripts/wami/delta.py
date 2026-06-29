"""델타 모드 — '최근 N일 vs 그 전 N일'의 행동 변화를 결정적으로 계산한다.

연 1회 Wrapped 회고가 아니라 *수시 점검*(/promptprint check)용. 길이에 강건한 비율 지표
(per-message rate · q_per_session)와 처방(skill_candidates: 최근 반복 노역)을 앞세운다 —
사용자 피드백의 #1 처방(1회용 novelty → 재사용 피드백 도구로 전환). 전부 stdlib·무네트워크."""
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Optional

from wami.model import QuestionRecord
from wami import textutil
from wami import aggregate as agg


def _parse(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _rate(n: int, total: int) -> float:
    return round(n / total, 3) if total else 0.0


def _window_metrics(records: List[QuestionRecord]) -> dict:
    """한 윈도우의 행동 지표(길이에 강건). 비율 = 신호가 1회+ 등장한 질문 수 / 전체."""
    total = len(records)
    sess_sizes = Counter(r.session_id for r in records)
    sessions = len(sess_sizes)
    one_shot = sum(1 for c in sess_sizes.values() if c == 1)
    sig_msgs = Counter()
    code = multistep = len_sum = 0
    for r in records:
        sigs = textutil.metaskill_signals(r.text)
        for k in agg.SIGNAL_KEYS:
            if sigs.get(k, 0):
                sig_msgs[k] += 1
        if textutil.has_code_block(r.text):
            code += 1
        if textutil.is_multistep(r.text):
            multistep += 1
        len_sum += len(r.text)
    return {
        "total": total,
        "sessions": sessions,
        "q_per_session": round(total / sessions, 2) if sessions else 0.0,
        "one_shot_rate": round(one_shot / sessions, 3) if sessions else 0.0,
        "avg_len": round(len_sum / total, 1) if total else 0.0,
        "code_block_rate": _rate(code, total),
        "multistep_rate": _rate(multistep, total),
        "metaskill_rate": {k: _rate(sig_msgs.get(k, 0), total) for k in agg.SIGNAL_KEYS},
    }


def _topic_counts(records: List[QuestionRecord]) -> Counter:
    c = Counter()
    for r in records:
        for t in set(textutil.tokens(r.text)):   # 질문당 1회만(빈도 왜곡 방지)
            c[t] += 1
    return c


def build_delta(records: List[QuestionRecord], window_days: int = 30,
                as_of: Optional[str] = None) -> dict:
    """최근/직전 두 윈도우로 잘라 행동 변화를 낸다.

    as_of 생략 시 마지막 레코드 날짜 기준(결정적). 윈도우는 half-open:
      recent = (as_of - W, as_of],  prior = (as_of - 2W, as_of - W]."""
    dated = [(r, _parse(r.ts)) for r in records]
    dated = [(r, d) for (r, d) in dated if d is not None]

    if not dated:
        empty_w = _window_metrics([])
        return {
            "window_days": window_days, "as_of": None, "empty": True,
            "recent": empty_w, "prior": empty_w, "deltas": {},
            "new_topics": [], "dropped_topics": [], "skill_candidates": [],
        }

    cutoff = (_parse(as_of) if as_of else None) or max(d for _, d in dated)
    w = timedelta(days=window_days)
    recent = [r for (r, d) in dated if cutoff - w < d <= cutoff]
    prior = [r for (r, d) in dated if cutoff - 2 * w < d <= cutoff - w]

    rm = _window_metrics(recent)
    pm = _window_metrics(prior)

    deltas = {
        "total": rm["total"] - pm["total"],
        "q_per_session": round(rm["q_per_session"] - pm["q_per_session"], 2),
        "one_shot_rate": round(rm["one_shot_rate"] - pm["one_shot_rate"], 3),
        "avg_len": round(rm["avg_len"] - pm["avg_len"], 1),
        "code_block_rate": round(rm["code_block_rate"] - pm["code_block_rate"], 3),
        "multistep_rate": round(rm["multistep_rate"] - pm["multistep_rate"], 3),
        "metaskill_rate": {
            k: round(rm["metaskill_rate"][k] - pm["metaskill_rate"][k], 3)
            for k in agg.SIGNAL_KEYS
        },
    }

    rt, pt = _topic_counts(recent), _topic_counts(prior)
    new_topics = [{"term": t, "count": c} for t, c in rt.most_common() if t not in pt][:8]
    dropped_topics = [{"term": t, "count": c} for t, c in pt.most_common() if t not in rt][:8]

    return {
        "window_days": window_days,
        "as_of": cutoff.date().isoformat(),
        "recent": {**rm, "start": (cutoff - w).date().isoformat(),
                   "end": cutoff.date().isoformat()},
        "prior": {**pm, "start": (cutoff - 2 * w).date().isoformat(),
                  "end": (cutoff - w).date().isoformat()},
        "deltas": deltas,
        "new_topics": new_topics,
        "dropped_topics": dropped_topics,
        # 처방: 최근 윈도우에서 반복·재설명하는 노역(스킬화 후보). aggregate L3 재사용.
        "skill_candidates": agg._skill_candidates(recent).get("candidates", []),
    }
