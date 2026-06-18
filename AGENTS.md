# AGENTS.md — where-am-i (Promptprint)

질문 로그로 전문성 성장을 보여주는 도구. **product-runtime** — 코드와 자기 `.brain` 루프를 소유한다(federation).
방법론은 공유 canon 을 *참조*하고(로컬 포크 금지), 여기엔 제품 특화 thin-overlay 만 둔다.

## 참조 (방법은 여기서; 이 파일은 제품 델타만)
- 운영 canon (WorkRun·safety K0–K5·EvidenceRef·Intent Lock·Lane) = `$S3_OS_ROOT/.claude/rules/{brain,session-workflow,safety}.md` — 참조만, 포크 금지
- 공용 substrate = `$MY_AI_MEMORY_ROOT/core/ESSENTIALS.md`
- 운영 루프 = 이 레포 `.brain/` (federation). 전략·조율 = s3-os 허브.
- 위계: 이 파일(제품 contract) > 공유 canon(방법). 충돌 시 canon 이 방법 정의, 이 파일은 제품 특화만.

## Mission
"Promptprint" — 사용자가 AI 코딩 에이전트(Claude Code·Codex)에 던진 **질문 로그**를 읽어, *질문 전문성*이 시간에 따라 어떻게 성장했는지 6차원 리포트로 보여준다(Spotify Wrapped 의 프롬프트판). 100% 로컬·무네트워크·오픈소스 — "데이터 안 보낸다"를 *코드로 검증* 가능하게.

## Source Boundaries — privacy-core (never-in-git, 불변)
- **읽기(read-only)**: `~/.claude/projects/` · `~/.codex/` (사용자 실제 프롬프트 로그). **수정·삭제 금지.**
- **쓰기(로컬 전용)**: `aggregates.json`·`insights.json`·리포트 HTML — cwd 에만. **절대 commit 금지**(실 질문 샘플 포함 — `.gitignore` 로 차단됨). K4.
- **네트워크 = 0** (불변·제품의 핵심 약속). 분석은 순수 Python stdlib·완전 오프라인. **network-capable import 추가 = founder 게이트**(프라이버시 약속 파기 위험·`verify.sh` 가 검증).
- 실 질문·식별자·PII = 로컬 산출물에만, git/`.brain`/허브 절대 금지. `.brain`·문서·픽스처 = 합성/익명 샘플만.

## Stack
Python stdlib(분석·의존성 0) · HTML 리포트 · Claude Code 플러그인(`.claude-plugin/`). 검증=`verify.sh`(network import grep·exit0=무네트워크 증명).

## Gates (founder 손 — 비가역)
- 🔒 플러그인 마켓플레이스 *공개 발행*·배포 = founder (`.claude-plugin/marketplace.json`).
- 🔒 네트워크 호출·외부 전송 도입 = founder (무네트워크 약속 위반).
- 🔒 GitHub origin push·force-push = founder. push 전 산출물(aggregates/insights/report) 추적 0 확인 필수.

## Validation (meaningful edit 후)
```bash
bash verify.sh                       # network import 0 (무네트워크 증명)
python3 -m pytest -q 2>/dev/null || true
git status --porcelain | grep -E 'aggregates|insights|report.*html' && echo "⚠ 산출물 추적됨" || echo "산출물 미추적 ✓"
git diff --check
```
