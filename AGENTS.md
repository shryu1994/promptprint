# AGENTS.md — where-am-i (Promptprint)

질문 로그로 전문성 성장을 보여주는 도구. 이 레포에서 작업하는 에이전트/LLM 이 지켜야 하는 규칙(자족 — 외부 의존 없음).

## Mission
"Promptprint" — 사용자가 AI 코딩 에이전트(Claude Code·Codex)에 던진 **질문 로그**를 읽어, *질문 전문성*이 시간에 따라 어떻게 성장했는지 6차원 리포트로 보여준다(Spotify Wrapped 의 프롬프트판). 100% 로컬·무네트워크·오픈소스 — "데이터 안 보낸다"를 *코드로 검증* 가능하게.

## Source Boundaries — privacy-core (never-in-git, 불변)
- **읽기(read-only)**: `~/.claude/projects/` · `~/.codex/` (사용자 실제 프롬프트 로그). **수정·삭제 금지.**
- **쓰기(로컬 전용)**: `aggregates.json`·`insights.json`·리포트 HTML — cwd 에만. **절대 commit 금지**(실 질문 샘플 포함 — `.gitignore` 로 차단됨).
- **네트워크 = 0** (불변·제품의 핵심 약속). 분석은 순수 Python stdlib·완전 오프라인. **network-capable import 추가 = 사람 승인 게이트**(프라이버시 약속 파기·`verify.sh` 가 검증).
- 실 질문·식별자·PII = 로컬 산출물에만, git 절대 금지. 문서·픽스처 = 합성/익명 샘플만.

## Stack
Python stdlib(분석·의존성 0) · HTML 리포트 · Claude Code 플러그인(`.claude-plugin/`). 검증=`verify.sh`(network import grep·exit0=무네트워크 증명).

## Gates (비가역 — 사람 승인)
- 🔒 플러그인 마켓플레이스 *공개 발행*·배포 (`.claude-plugin/marketplace.json`).
- 🔒 네트워크 호출·외부 전송 도입 (무네트워크 약속 위반).
- 🔒 GitHub origin push·force-push. push 전 산출물(aggregates/insights/report) 추적 0 확인 필수.

## 작업 규율
- 되돌릴 수 없는 행위(push·발행·배포·광범위 삭제)는 멈추고 승인받는다. 읽기·분석은 자유.
- 완료 주장 전 검증을 실제 실행한다(아래 Validation). 추측 신지식·미검증 완료 주장 금지.

## Validation (meaningful edit 후)
```bash
bash verify.sh                       # network import 0 (무네트워크 증명)
python3 -m pytest -q 2>/dev/null || true
git status --porcelain | grep -E 'aggregates|insights|report.*html' && echo "⚠ 산출물 추적됨" || echo "산출물 미추적 ✓"
git diff --check
```
