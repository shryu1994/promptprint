#!/usr/bin/env python3
"""PreToolUse irreversible-action guard — Bash 비가역 명령을 founder 게이트로.

trunk 안전 레이어 (P4). safety.md §Stop 의 비가역 명령을 **Bash 도구 경유로도** 가로챈다.
= guard-paths.py(Edit/Write 한정)의 H1 갭(Bash 우회) 보완.

두 단계 결정:
- **ask** (프롬프트): push/force-push/amend/git config 변경/배포(gcloud·terraform·vercel)/
  publish/merge — founder 가 *가끔 의도하는* 비가역 → 다이얼로그로 승인받음(allow-list 도 덮어씀).
- **deny** (하드차단): 카탈로그형 rm(/,~,$HOME,/*,.git)·git history 재작성(filter-repo/branch)
  — 에이전트가 *해선 안 되는* 파국 → 막음(fat-finger 승인 방지).

경계(정직): 에이전트의 Bash 호출에만 발동(founder 의 직접 터미널 명령엔 영향 0). 허용은 침묵.
파싱불가/비-Bash 는 개입 안 함. 우회 가능(obfuscation) — defense-in-depth 이지 airtight 아님.
의존: 표준 라이브러리만. ask/deny 스키마 = Claude Code hooks 문서 검증(2026-06-18).
"""
import json
import re
import sys

# (정규식, 결정, 사유) — 매치 시 결정 적용. safety.md §Stop 과 정합.
RULES = [
    (re.compile(r"\bgit\s+push\b", re.I), "ask",
     "git push (force 포함) — push 전 `git fetch` 로 stale 확인 권고"),
    (re.compile(r"\bgit\s+commit\b[^\n]*--amend", re.I), "ask", "git commit --amend (이력 변경)"),
    (re.compile(r"\bgit\s+config\b(?![^\n]*(--get|--list|--get-all|--get-regexp|\s-l\b))", re.I),
     "ask", "git config 변경 (읽기 --get/--list 는 허용)"),
    (re.compile(r"\bgcloud\b[^\n]*\bdeploy\b", re.I), "ask", "gcloud deploy (배포)"),
    (re.compile(r"\bgcloud\s+builds\s+submit\b", re.I), "ask", "gcloud builds submit (배포 빌드)"),
    (re.compile(r"\bterraform\s+apply\b", re.I), "ask", "terraform apply (인프라 변경)"),
    (re.compile(r"\bvercel\b[^\n]*(--prod|\bdeploy\b)", re.I), "ask", "vercel 배포"),
    (re.compile(r"\bnpm\s+publish\b", re.I), "ask", "npm publish (공개 발행)"),
    (re.compile(r"\bdocker\s+push\b", re.I), "ask", "docker push (레지스트리 발행)"),
    (re.compile(r"\bkubectl\s+(apply|delete)\b", re.I), "ask", "kubectl apply/delete (런타임 변경)"),
    (re.compile(r"\bgh\s+(release\s+create|pr\s+merge)\b", re.I), "ask", "gh release/pr merge (발행/머지)"),
    # 파국 — 하드차단(deny):
    (re.compile(r"\bgit\s+(filter-repo|filter-branch)\b", re.I), "deny",
     "git history 재작성(filter-repo/branch)"),
    (re.compile(r"\brm\s+(-[a-zA-Z]+\s+)*(/|~|\$HOME|/\*|\.git)(\s|/|$|\*)", re.I), "deny",
     "위험 경로 rm (/, ~, $HOME, /*, .git)"),
]


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # 파싱 불가 → 개입 안 함
    if data.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = (data.get("tool_input", {}) or {}).get("command", "") or ""
    for rx, decision, reason in RULES:
        if rx.search(cmd):
            prefix = ("⚠ 비가역 — founder 승인 필요" if decision == "ask"
                      else "🛑 비가역 차단 (founder 게이트)")
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": f"{prefix}: {reason}",
                }
            }
            print(json.dumps(out, ensure_ascii=False))
            sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
