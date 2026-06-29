"""오디언스 템플릿별 데이터 정제 (결정적, stdlib only).

템플릿:
  personal  — 정제 없음(개인 확인용, 전부 표시).
  corporate — 집계·익명화 최대(사내 보고용): 샘플 원문 제거 + 프로젝트명 익명화 + 인용 제거.
  social    — SNS 공유용: corporate 정제 + hero/cards 만 렌더.

핵심: 정제는 *집계 단계*에서 적용돼, 민감 텍스트가 LLM 입력(aggregates.json)에
들어가기 전에 차단된다. strip_quotes/sanitize_insights는 렌더 단계 2차 방어.
"""
import copy
import re

TEMPLATES = ("personal", "corporate", "social")

_ALL_SECTIONS = {"hero", "chart", "chapters", "dims", "cards", "bearings", "skills"}

# 템플릿 → 렌더에 포함할 섹션
_SECTIONS = {
    "personal": set(_ALL_SECTIONS),
    "corporate": set(_ALL_SECTIONS),       # 전 섹션, 단 내용은 정제됨
    "social": {"hero", "cards"},           # 공유 카드 중심
}

# 템플릿 → 정제 정책
_POLICY = {
    "personal": {"drop_text": False, "anon_project": False},
    "corporate": {"drop_text": True, "anon_project": True},
    "social": {"drop_text": True, "anon_project": True},
}


def _norm(template) -> str:
    return template if template in TEMPLATES else "personal"


def is_redacted(template) -> bool:
    """personal 외(corporate/social)면 정제 대상."""
    pol = _POLICY[_norm(template)]
    return pol["drop_text"] or pol["anon_project"]


def section_policy(template) -> set:
    return set(_SECTIONS[_norm(template)])


def redact_samples(stratified, template):
    """샘플 리스트를 템플릿 정책대로 정제한 새 리스트를 반환(입력 비파괴).

    corporate/social: 원문 text 제거 + project를 결정적 익명 라벨(project-N)로.
    같은 원본 프로젝트는 같은 라벨로 매핑(일관성)."""
    pol = _POLICY[_norm(template)]
    if not pol["drop_text"] and not pol["anon_project"]:
        return [dict(s) for s in stratified]

    label = {}
    out = []
    for s in stratified:
        d = dict(s)
        if pol["drop_text"]:
            d["text"] = ""
        if pol["anon_project"]:
            proj = s.get("project")
            if proj:
                if proj not in label:
                    label[proj] = f"project-{len(label) + 1}"
                d["project"] = label[proj]
        out.append(d)
    return out


def redaction_summary(stratified, template) -> dict:
    """정제 영수증 — 공유본(corporate/social)에서 *실제로 한 일*을 카운트한다.

    탐지(예: '시크릿 N건 발견')가 아니라 정제 동작을 그대로 센다(과장 금지·정직):
      raw_texts_removed   = 원문이 비워진 샘플 질문 수(drop_text)
      projects_anonymized = project-N 라벨로 익명화된 서로 다른 프로젝트 수(anon_project)
    personal 은 정제 0(receipt 없음). 입력 비파괴·결정적."""
    pol = _POLICY[_norm(template)]
    raw_texts_removed = (
        sum(1 for s in stratified if (s.get("text") or "").strip())
        if pol["drop_text"] else 0
    )
    projects_anonymized = (
        len({s.get("project") for s in stratified if s.get("project")})
        if pol["anon_project"] else 0
    )
    return {
        "template": _norm(template),
        "redacted": is_redacted(template),
        "raw_texts_removed": raw_texts_removed,
        "projects_anonymized": projects_anonymized,
    }


# 큰/곱은따옴표로 둘러싼 인용 덩어리는 제거한다. 홑따옴표는 '인용처럼' 쓰일 때만 —
# 앞뒤가 글자/숫자가 아닐 때만 — 제거해 축약형(don't)·소유격(worker's)은 보존한다.
_QUOTE = re.compile(
    r'["“”][^"“”]*["“”]'                          # 쌍/곱은따옴표 인용
    r"|(?<![\w'‘’])['‘][^'‘’\n]*['’](?![\w'‘’])"  # 홑따옴표 인용(축약형/소유격 제외)
)


def strip_quotes(s):
    """문자열에서 인용 덩어리("…"/“…”)를 제거(렌더 2차 방어). 비문자열은 그대로."""
    if not isinstance(s, str):
        return s
    return _QUOTE.sub("…", s).strip()


def _strip_list(items):
    return [strip_quotes(x) if isinstance(x, str) else x for x in (items or [])]


def sanitize_insights(insights):
    """insights의 렌더되는 문자열에서 인용을 제거한 깊은 복사본을 반환(입력 비파괴).
    corporate/social 렌더 전에 적용한다."""
    ins = copy.deepcopy(insights or {})
    for k in ("headline", "summary"):
        if isinstance(ins.get(k), str):
            ins[k] = strip_quotes(ins[k])
    for dim in (ins.get("dimensions") or {}).values():
        if isinstance(dim, dict):
            if isinstance(dim.get("narrative"), str):
                dim["narrative"] = strip_quotes(dim["narrative"])
            dim["evidence"] = _strip_list(dim.get("evidence"))
    for c in (ins.get("chapters") or []):
        if isinstance(c, dict) and isinstance(c.get("narrative"), str):
            c["narrative"] = strip_quotes(c["narrative"])
    for b in (ins.get("next_bearings") or []):
        if isinstance(b, dict):
            for f in ("why", "how"):
                if isinstance(b.get(f), str):
                    b[f] = strip_quotes(b[f])
    for c in (ins.get("cards") or []):
        if isinstance(c, dict):
            for f in ("headline", "stat", "caption"):
                if isinstance(c.get(f), str):
                    c[f] = strip_quotes(c[f])
    for s in (ins.get("skill_suggestions") or []):
        if isinstance(s, dict):
            for f in ("why", "seed", "est_savings"):
                if isinstance(s.get(f), str):
                    s[f] = strip_quotes(s[f])
            if s.get("evidence") is not None:
                s["evidence"] = _strip_list(s.get("evidence"))
    return ins
