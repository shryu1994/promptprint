import re
from datetime import datetime, timezone

# --- 타임스탬프 정규화 ---------------------------------------------------------

def norm_ts(raw) -> str:
    """Normalize an ISO timestamp to UTC ISO. Returns '' if unparseable.
    Strips sub-second fraction so it parses on Python 3.10 (whose fromisoformat
    rejects fractional-seconds + offset)."""
    if not isinstance(raw, str) or not raw:
        return ""
    s = raw.strip().replace("Z", "+00:00")
    s = re.sub(r"\.\d+", "", s, count=1)  # drop the fractional-seconds part
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return ""


# --- 노이즈 판정 -------------------------------------------------------------
# 실제 Claude 로그에서 관측된 시스템/명령 주입 마커들.
NOISE_PREFIXES = (
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<local-command",
    "<bash-input",
    "<bash-stdout",
    "<bash-stderr",
    "<user-prompt-submit-hook",
    "<system-reminder>",
    "[Request interrupted",
    # 실제 로그에서 확인된 시스템 주입 태그 (Task 13 real-data feedback)
    "<task-notification",
    "<subagent_notification",
    "<environment_context",
    "<goal_context",
    "<turn_aborted",
    "<ide_opened_file",
    "<create-pr-command",
    "<task>",
    # Codex가 user 메시지로 주입하는 IDE 컨텍스트·AGENTS (실데이터 발견: user 텍스트의 ~84%)
    "# Context from my IDE setup",
    "# AGENTS.md instructions",
    # claude-mem 플러그인이 user 턴으로 주입하는 기억 에이전트 프롬프트·관찰 XML
    # (실데이터: 자동화-heavy 환경에서 user 텍스트의 ~50% — 진짜 질문 아님).
    "Hello memory agent",
    "<observed_from_primary_session",
    "--- MODE SWITCH:",
    "You are a Claude-Mem",
    "You are Claude-Mem",
    "You are extracting a structured summary",
    # Claude Code 자체 시스템/요약/스킬/훅 주입 (사람이 친 질문이 아님)
    "This session is being continued from a previous",
    "Caveat: The messages below were generated",
    "Continue from where you left off.",
    "[Your previous response had no visible output",
    "Base directory for this skill:",
    "Stop hook feedback:",
    "A session-scoped Stop hook is now active",
)


def is_noise(text) -> bool:
    """사용자가 실제로 친 질문이 아니면 True."""
    if not isinstance(text, str):
        return True
    s = text.strip()
    if not s:
        return True
    for p in NOISE_PREFIXES:
        if s.startswith(p):
            return True
    return False


# --- 코드블록 / 멀티스텝 ------------------------------------------------------
def has_code_block(text: str) -> bool:
    return "```" in text


_NUM_STEP = re.compile(r"(?m)^\s*\d+[.)]\s+\S")
_KO_SEQ = re.compile(r"(먼저|그다음|그 다음|그리고 나서|이후에)")
# 한국어 순서 표현이 포함됐더라도 너무 짧은 구문은 멀티스텝으로 보지 않음 (단순 어절 수준 필터)
_MIN_MULTISTEP_LEN = 12


def is_multistep(text: str) -> bool:
    if len(_NUM_STEP.findall(text)) >= 2:
        return True
    if _KO_SEQ.search(text) and len(text) > _MIN_MULTISTEP_LEN:
        return True
    return False


# --- 토큰화 ------------------------------------------------------------------
# 영문 단어 + 한글 어절. 결정적.
_TOKEN = re.compile(r"[A-Za-z]{2,}|[가-힣]{2,}")
_STOP_EN = {
    "the", "is", "are", "a", "an", "to", "of", "and", "or", "in", "on", "for",
    "it", "this", "that", "with", "do", "does", "how", "what", "why", "i", "you",
    "be", "can", "if", "so", "my", "me", "we", "as", "at", "by", "from",
    # 경로·파일 메타 토큰 (주제가 아니라 경로 조각 — 실데이터에서 top_terms 오염)
    "file", "files", "md", "src", "repo", "repos", "user", "users",
    "workspace", "dir", "path", "id",
    # 순수 기능어 (주제 신호 아님)
    "only", "not", "no", "any", "new", "read", "open", "active", "set", "get",
    "run", "use", "using", "add", "make", "want", "need", "just", "now", "here",
    "also", "all", "into", "then", "out", "up", "when", "will", "should",
    "has", "have", "was", "were", "been", "but", "about", "more", "some", "than",
    # 코드/제어흐름 보일러플레이트 (주제 아님 — 실데이터에서 top_terms 오염)
    "return", "name", "line", "one", "each", "step", "pass", "value", "values",
    "none", "true", "false", "null", "self", "def", "var", "let", "const",
    "print", "item", "items", "list", "dict",
}
# 한글 기능어·조사·지시어 (어절 통째라 stopword 로 거른다)
_STOP_KO = {
    # 단독 조사 토큰 (예: "API에서" → "에서")
    "에서", "으로", "에게", "한테", "까지", "부터", "처럼", "보다", "마다",
    "조차", "에는", "에도", "라고", "라는",
    # 접속·지시·부사 기능어
    "그리고", "하지만", "그런데", "그래서", "지금", "현재", "실제", "정도",
    "경우", "자체", "이런", "그런", "저런", "어떤", "무슨", "다시", "또한",
    "그냥", "진짜", "약간", "너무", "여기", "거기", "저기", "이것", "그것",
    "저것", "이거", "그거", "저거", "우리", "통해", "위해", "대해", "관련",
}
# 어절 끝 조사 (긴 것부터 — 한 번만, stem 이 2자+ 일 때만 떼어낸다)
_JOSA = sorted(
    [
        "으로서", "으로써", "에서는", "에게서",
        "으로", "에서", "에게", "한테", "까지", "부터", "처럼", "보다",
        "마다", "조차", "에는", "에도",
        "은", "는", "이", "가", "을", "를", "에", "의", "도", "만", "과", "와", "로",
    ],
    key=len, reverse=True,
)


def _strip_josa(w: str) -> str:
    """한글 어절에서 끝 조사 1개를 떼어낸다. stem 이 2자 미만이 되면 그대로 둔다."""
    for j in _JOSA:
        if w.endswith(j) and len(w) - len(j) >= 2:
            return w[: -len(j)]
    return w


def tokens(text: str) -> list:
    out = []
    for m in _TOKEN.finditer(text):
        w = m.group(0)
        if w[0].isascii():            # 영문 토큰
            w = w.lower()
            if w in _STOP_EN:
                continue
        else:                          # 한글 어절 — 끝 조사 스트립 후 불용어 거름
            w = _strip_josa(w)
            if w in _STOP_KO:
                continue
        out.append(w)
    return out


# --- 메타스킬 신호 ------------------------------------------------------------
# 한/영 양쪽 휴리스틱. 각 카테고리의 정규식 매치 횟수를 센다.
_SIGNAL_PATTERNS = {
    "critique": re.compile(r"비판|문제점|단점|리스크|critique|trade-?off|드러내|critical review"),
    "verify": re.compile(r"검증|맞는지|맞나|확실|정말 맞|제대로 (됐|된|되)|are you sure|double[- ]?check|verify|확인해 ?줘\?|정말이?야\?"),
    "delegate": re.compile(r"알아서|네가 정|추천|골라|결정해|decide|you choose|your call"),
    "counter": re.compile(r"왜 안|왜 굳이|왜 그렇|어째서|근거|이유가|이유는|why not|why should|rationale"),
}


def metaskill_signals(text: str) -> dict:
    return {k: len(p.findall(text)) for k, p in _SIGNAL_PATTERNS.items()}


# --- 질문 장르 분류 (heuristic v1) --------------------------------------------
# 의도(무엇을 하려는가) 기준 4종 + other. 한 질문 = 정확히 한 장르(공유용 mix).
# 결정적·양언어·투명(패턴 공개→튜닝 가능). 우선순위 = 리스트 순서(첫 매치 승):
#   debug → improve → understand → build → other.
# (debug 가 가장 구체적 — "구현했는데 에러" 는 debug. understand 는 개념 질문만:
#  맨 "how" 는 build 로 — 대부분의 코딩 질문 "how do I X" 는 *하려는* 의도라서.)
GENRES = ("debug", "build", "understand", "improve", "other")

_GENRE_PATTERNS = [
    ("debug", re.compile(
        r"버그|에러|오류|안 ?(돼|된다|됨|되는)|왜 안|고쳐|디버그|실패|크래시|먹통|"
        r"\bbug\b|error|\bfix\b|broken|\bfail|crash|exception|stack ?trace|"
        r"doesn'?t work|not working|won'?t")),
    ("improve", re.compile(
        r"리팩|개선|정리|최적화|단순화|깔끔|느려|빠르게|"
        r"refactor|optimi[sz]|clean ?up|simplif|improve|faster|\bperf\b|rename|tidy|streamline")),
    ("understand", re.compile(
        r"설명|이해|의미|차이|무엇|뭐(야|예요|죠|니|지)|왜 (그|이|저|되)|원리|어떻게 (동작|작동|돌아)|"
        r"explain|what (is|are|does|happens)|why (does|is|are|do)|how does|"
        r"difference between|conceptually")),
    ("build", re.compile(
        r"구현|만들|추가|작성|생성|짜 ?줘|스크립트|"
        r"how (do|can|to) ?i?\b|implement|build|create|\badd\b|write |generate|make |set ?up")),
]


def classify_genre(text) -> str:
    """질문을 의도 장르 하나로 분류한다(heuristic v1, 결정적). 매치 없으면 'other'."""
    if not isinstance(text, str):
        return "other"
    for genre, pat in _GENRE_PATTERNS:
        if pat.search(text):
            return genre
    return "other"
