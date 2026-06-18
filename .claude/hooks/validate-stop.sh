#!/usr/bin/env bash
# Advisory Stop hook — graph lint + precise secret-value scan + secret-file find.
# NON-BLOCKING by design: always exit 0. Emits {"systemMessage": ...} only when an
# actual issue is found. Skips silently when there are no uncommitted changes, so
# turns that touch nothing add zero behavior. (trunk skeleton-first 첫 실행 레이어)
#
# 의존: git, python3, grep (POSIX). rg 는 일부 환경에서 불안정해 의도적으로 미사용.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT" 2>/dev/null || exit 0

# 0. No uncommitted changes (working tree + index + untracked) → nothing to check.
if git diff --quiet 2>/dev/null \
   && git diff --cached --quiet 2>/dev/null \
   && [ -z "$(git ls-files --others --exclude-standard 2>/dev/null)" ]; then
  exit 0
fi

changed="$(
  { git diff --name-only --diff-filter=ACM HEAD 2>/dev/null
    git ls-files --others --exclude-standard 2>/dev/null; } | sort -u
)"

issues=""

# 1. graph lint — report errors only (warnings advisory elsewhere).
if [ -f tools/llm_wiki_graph_lint.py ]; then
  python3 tools/llm_wiki_graph_lint.py --root . \
    --include-learn --include-sample-vault --include-architecture \
    --report /tmp/.stop-hook-lint.json >/dev/null 2>&1
  errs="$(python3 -c "import json;d=json.load(open('/tmp/.stop-hook-lint.json'));print((d.get('summary',d)).get('counts',{}).get('error',0))" 2>/dev/null || echo 0)"
  case "$errs" in ''|*[!0-9]*) errs=0;; esac
  [ "$errs" -gt 0 ] && issues="${issues}graph-lint errors=${errs}; "
fi

# precise secret-VALUE regex (actual tokens, NOT broad policy-text markers).
SECRET_RE='sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[0-9A-Za-z-]{10,}|ghp_[A-Za-z0-9]{36}'

# 2. secret-VALUE scan on changed files (grep -E, per file).
if [ -n "$changed" ]; then
  hit=""
  while IFS= read -r f; do
    [ -n "$f" ] && [ -f "$f" ] || continue
    if grep -Eq "$SECRET_RE" "$f" 2>/dev/null; then
      hit="${hit}${f} "
    fi
  done <<EOF
$changed
EOF
  [ -n "$hit" ] && issues="${issues}secret-value 의심: ${hit}; "
fi

# 3. secret-FILE among changes (.env/.db/.sqlite/.pem/.p12).
sfiles="$(printf '%s\n' "$changed" | grep -iE '\.(env|db|sqlite|pem|p12)$' 2>/dev/null | head -5 | tr '\n' ' ')"
[ -n "$sfiles" ] && issues="${issues}secret-file: ${sfiles}; "

# emit advisory only when something was found; never block.
if [ -n "$issues" ]; then
  msg="$(printf '%s' "⚠ Stop-hook advisory: ${issues}(non-blocking — 검토 후 commit)" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  printf '{"systemMessage": "%s", "suppressOutput": true}\n' "$msg"
fi
exit 0
