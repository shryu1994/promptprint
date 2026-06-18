#!/usr/bin/env python3
"""SessionStart/Stop federation 신선도 advisory — `.brain` 가 git HEAD 보다 뒤처지면 경고.

allo 06-14 freeze 류 드리프트(작업은 06-18 인데 `.brain` 은 06-14) 방지. 제품 레포가
허브로 떠내려가거나 ledger 미기록으로 굳는 걸 세션 시작/종료에 가볍게 알린다.

판정 (모두 git HEAD %cs 대비 — 결정론적, wall-clock 의존 0):
- brain_date = `.brain/work/now.md` 의 `last_verified` (있으면) → 없으면 now.md **mtime** 폴백.
- HEAD 커밋날짜가 brain_date 보다 MAX_DRIFT_DAYS(기본 3, env override) **초과** 뒤처지면 경고.
- `runs/INDEX.md` 있으면 마지막 `run-YYYYMMDD` 가 HEAD 보다 초과 뒤처지면 별도 경고(ledger drift).

경계(정직): **non-blocking advisory** (safety.md (advisory) 층) — 차단 안 함, 절대 exit 2 안 함.
경고는 founder/agent 가 보고 판단·refresh 하는 신호이지 기계강제가 아니다. `.brain/work/now.md`
없음·git HEAD 없음(`no_head`, AGENTS.md 정합) = 무음 no-op → 레포 독립·multi-machine resilient.
의존: 표준 라이브러리 + git. 스키마 = Claude Code hooks 문서 검증(2026-06-18).
"""
import json
import os
import re
import subprocess
import sys
from datetime import date

_LV_RE = re.compile(r"(?m)^last_verified:\s*(\d{4}-\d{2}-\d{2})")
_RUN_RE = re.compile(r"run-(\d{8})")


def _max_days() -> int:
    try:
        return int(os.environ.get("BRAIN_FRESHNESS_MAX_DAYS", "3"))
    except ValueError:
        return 3


def head_date(root: str):
    """git HEAD committer date (YYYY-MM-DD) 또는 None (no HEAD)."""
    try:
        r = subprocess.run(["git", "-C", root, "log", "-1", "--format=%cs"],
                           capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    out = (r.stdout or "").strip()
    return out if (r.returncode == 0 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", out)) else None


def brain_date(now_path: str):
    """(YYYY-MM-DD, basis). last_verified 우선, 없으면 now.md mtime 날짜."""
    try:
        text = open(now_path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None, None
    m = _LV_RE.search(text)
    if m:
        return m.group(1), "last_verified"
    return date.fromtimestamp(os.path.getmtime(now_path)).isoformat(), "mtime"


def index_run_date(index_path: str):
    """runs/INDEX.md 마지막 run-YYYYMMDD → YYYY-MM-DD, 또는 None."""
    try:
        text = open(index_path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    runs = _RUN_RE.findall(text)
    if not runs:
        return None
    d = runs[-1]
    return f"{d[0:4]}-{d[4:6]}-{d[6:8]}"


def _diff(later: str, earlier: str):
    try:
        return (date.fromisoformat(later) - date.fromisoformat(earlier)).days
    except ValueError:
        return None


def assess(brain_ymd, basis, head_ymd, index_ymd, max_days):
    """뒤처짐 경고 목록(빈 = fresh). 전부 HEAD 대비."""
    warnings = []
    if not head_ymd:
        return warnings  # no HEAD → 판정 불가, no-op
    if brain_ymd:
        d = _diff(head_ymd, brain_ymd)
        if d is not None and d > max_days:
            warnings.append(f"now.md {basis}({brain_ymd}) 가 git HEAD({head_ymd}) 보다 {d}일 뒤처짐")
    if index_ymd:
        d = _diff(head_ymd, index_ymd)
        if d is not None and d > max_days:
            warnings.append(f"runs/INDEX.md 마지막 run({index_ymd}) 이 HEAD({head_ymd}) 보다 {d}일 뒤처짐")
    return warnings


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    event = data.get("hook_event_name", "")
    root = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    now_path = os.path.join(root, ".brain", "work", "now.md")
    if not os.path.isfile(now_path):
        sys.exit(0)  # federation .brain 없음 → no-op (허브 비제품·resilient)

    hd = head_date(root)
    bd, basis = brain_date(now_path)
    idx = index_run_date(os.path.join(root, ".brain", "work", "runs", "INDEX.md"))
    warnings = assess(bd, basis, hd, idx, _max_days())
    if not warnings:
        sys.exit(0)

    msg = ("⚠ .brain 신선도(advisory·non-blocking): " + " · ".join(warnings)
           + " — 세션 작업이 이 레포 `.brain` 에 반영됐는지 확인하라"
           " (federation: 제품 작업은 허브 아닌 *제품 레포* `.brain` 에 기록). 판단은 founder/operator.")

    if event == "SessionStart":
        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": msg,
            },
            "systemMessage": msg,
        }
    else:  # Stop (및 그 외) — validate-stop.sh 와 동형 advisory
        out = {"systemMessage": msg, "suppressOutput": True}
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
