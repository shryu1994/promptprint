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
}


def tokens(text: str) -> list:
    out = []
    for m in _TOKEN.finditer(text):
        w = m.group(0).lower()
        if w in _STOP_EN:
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
