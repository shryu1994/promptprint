<div align="center">

<a href="https://sh-ryu.com/promptprint/"><img src="assets/banner.png" alt="Promptprint — 당신이 AI 코딩 에이전트에게 어떻게 묻는지 로컬에서 점검" width="760"></a>

[English](README.md) · **한국어**

[![CI](https://github.com/shryu1994/promptprint/actions/workflows/ci.yml/badge.svg)](https://github.com/shryu1994/promptprint/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-8A5A1A?style=flat-square)](LICENSE)
[![dependencies](https://img.shields.io/badge/dependencies-0-46604E?style=flat-square)](#️-동작-방식)
[![network calls](https://img.shields.io/badge/network-0-46604E?style=flat-square)](#-직접-검증)
[![stars](https://img.shields.io/github/stars/shryu1994/promptprint?style=flat-square&color=8A5A1A&label=stars)](https://github.com/shryu1994/promptprint/stargazers)

*공은 AI 에이전트가 가져갑니다. Promptprint는* **당신이** *얼마나 잘 *묻게* 됐는지, 그리고 다음에 뭘 고치면 되는지 보여줍니다.*

[**▶ 라이브 데모 리포트**](https://sh-ryu.com/promptprint/) · [GitHub](https://github.com/shryu1994) · [X / Twitter](https://x.com/shryu1994) · [sh-ryu.com](https://sh-ryu.com)

</div>

---

Promptprint는 당신이 **AI 코딩 에이전트(Claude Code, Codex)에 던진 질문**을 100% 당신의 컴퓨터에서 읽어, 다른 어떤 도구도 안 재는 것을 잽니다 — **당신이 *어떻게* 묻는지, 그리고 그게 어떻게 변하는지.**

다른 도구는 전부 *에이전트*를 잽니다(토큰·비용·받아들인 코드 줄 수). 이건 당신의 질문 실력에 대한 **수시 점검**이고, 기분 좋아지는 숫자가 아니라 *다음에 뭘 바꿀지*로 끝납니다. 오픈소스이고 설계상 오프라인이라, *"데이터가 컴퓨터를 떠나지 않는다"*를 믿는 게 아니라 **코드로 검증**할 수 있습니다.

> **MIT · 표준 라이브러리만 · 네트워크 0.** `bash verify.sh`는 네트워크 가능 import가 하나도 없을 때만 `0`을 반환합니다.

<div align="center">

[<img src="examples/demo/report-preview.png" alt="Promptprint 데모 리포트 — 5개월간 질문이 어떻게 자랐는지 보여주는 필드 저널" width="720">](https://sh-ryu.com/promptprint/)

**▶ [라이브 데모 리포트 보기 →](https://sh-ryu.com/promptprint/)** — 100% 합성 데이터로 제작, 실제 프롬프트 없음.

</div>

## 설치

Claude Code(또는 Codex)에서 — 따로 준비할 것 없습니다:

```
/plugin marketplace add shryu1994/promptprint
/plugin install promptprint@promptprint
/promptprint:promptprint
```

스킬이 내장 Python(표준 라이브러리만)을 실행하고, **해석은 당신이 이미 쓰는 에이전트가** 합니다 — 별도 모델도, API 키도 없습니다.

<details>
<summary>📖 <b>목차</b></summary>

- [🎯 무엇을 얻나](#-무엇을-얻나)
- [⚙️ 동작 방식](#️-동작-방식)
- [🔒 직접 검증](#-직접-검증)
- [🙅 이게 못 재는 것](#-이게-못-재는-것)
- [🛡️ 프라이버시](#️-프라이버시)
- [🔌 지원 도구](#-지원-도구)
- [🤝 연결](#-연결)

</details>

## 🎯 무엇을 얻나

**수시 점검 — 실제로 다시 돌리게 되는 것.** `/promptprint check`는 최근 30일과 그 전 30일을 비교합니다: *어떻게 묻는지*가 뭐가 변했나(검증을 더? 위임을 더? 작업당 왕복이 줄었나?), 새로 밟은 땅은 어디, 그리고 — 가장 유용한 — **매번 다시 설명하는 반복 작업을, 또 붙여넣지 말고 스킬로 만들 준비된 형태로.** 길이에 강건한 비율이지, 부풀려진 원시 횟수가 아닙니다.

**성장 리포트** — 자족적인 HTML 필드 저널 한 장(+ 공유 카드), 당신의 언어로. **다음에 뭘 할지**로 열립니다 — 다음 방위, 그리고 로그 속 반복 작업에서 만들 스킬(각각 붙여넣기만 하면 되는 `/skill-creator` seed + *정직하게 추정으로 표기한* 절감치) — 그다음 6차원 회고가 이어집니다:

| 차원 | 무엇을 담나 |
|---|---|
| **주제 진화** | 무엇을 *묻는지*, 그 땅이 어떻게 옮겨가고 깊어지는지 |
| **깊이** | "어떻게 하지…"(절차) → "왜 이게 더 낫지…"(원리·트레이드오프) |
| **AI 메타스킬** | 받아쓰기 → 지휘·검증: AI를 *다루는* 성숙도 |
| **정교함** | 맥락·제약·멀티스텝 — 의도당 왕복을 줄임 |
| **숙달** | 한때 집중해 묻다가 *졸업한* 주제들 |
| **당신의 국면** | 데이터에서 도구가 찾은 군집 — 당신만의 작업 계절 |

또한 **과하게 노출하지 않고 공유할 수 있는** 두 가지를 보여줍니다: **세션 모양**(작업당 왕복수·원샷률 — 실제로 바꿀 수 있는 숫자)과 **질문 장르 믹스**(디버그 / 구현 / 이해 / 개선) — *무엇을* 묻는지의 결을, 원문 없이 수치로만.

## ⚙️ 동작 방식

5개 레이어, 전부 당신의 컴퓨터에서:

1. **로그** — `~/.claude`·`~/.codex`에서 질문을 읽음(읽기 전용).
2. **어댑터** — 각 도구 포맷을 하나의 공통 스키마로 정규화.
3. **집계** — 결정적 Python 통계: LLM 없음, 같은 입력 → 같은 숫자.
4. **해석** — 당신의 에이전트가 집계 + 작은 샘플(전체 대화 아님)을 읽고 서사를 씀.
5. **렌더** — 자족적 HTML 리포트 한 장 + 공유 카드 몇 개.

신뢰를 지키는 두 축: **결정적 골격**(실행마다 안 변하는 순수 Python 숫자) + 그 위의 **LLM 서사**, 그리고 **당신의 에이전트가 엔진** — 별도 모델도 API 키도 없음.

## 🔒 직접 검증

Promptprint는 당신의 가장 사적인 로그를 읽습니다 — 그래서 절대 외부로 보내지 않음을 **코드로** 증명합니다:

<div align="center">
<img src="assets/verify.gif" alt="bash verify.sh가 네트워크 import를 스캔하고 0을 반환" width="560">
</div>

```bash
bash verify.sh
```

한 명령이 분석 코드에서 네트워크 가능 import를 스캔하고, 하나도 없을 때만 `0`을 반환합니다. 증명은 약속이 아니라 코드 안에 있습니다. **공유 안전 영수증:** 팀/소셜용 리포트(corporate/social)는 무엇을 가렸는지 영수증을 달고 나옵니다 — 원문 질문 제거·프로젝트명 익명화·네트워크 0 — "안전하게 공유 가능"을 *보여줍니다*, 가정하지 않고.

## 🙅 이게 못 재는 것

정직함이 핵심이라, 숫자가 멈추는 지점을 밝힙니다:

- **장르 믹스는 휴리스틱이지 판정이 아닙니다.** "디버그/구현/이해/개선"은 표현에서 패턴 매칭한 거친 결일 뿐, 당신에 대한 라벨이 아닙니다.
- **왕복이 적은 게 항상 더 좋은 건 아닙니다.** 어려운 문제는 본래 더 많은 주고받음이 필요합니다 — 도구는 *추세*를 보여주지, 쫓아야 할 점수가 아닙니다.
- **한 달 미만 데이터는 추세가 아니라 스냅샷**이고, 리포트가 스스로 그렇게 말합니다(`confidence_tier`).
- **절감치는 추정입니다.** 스킬 제안 뒤의 횟수는 실측이지만, 절약 시간은 가정을 노출한 추정으로 표기됩니다. 조작된 ROI 없음.

## 🛡️ 프라이버시

질문은 사적이라, 프라이버시는 설계에 내장돼 있습니다 — 나중에 덧붙인 게 아니라:

- **읽기 전용.** Promptprint는 로그를 읽기만 하고 절대 바꾸지 않습니다.
- **네트워크 0.** 분석은 순수 Python 표준 라이브러리이고 완전 오프라인입니다.
- **로컬 산출물.** `aggregates.json`·`insights.json`·리포트는 당신의 실제 질문을 담습니다. 기본적으로 git에서 제외되니 — 커밋하지 말고, 공유 전 카드를 확인하세요.
- 텔레메트리·계정·가입 없음.

## 🔌 지원 도구

| 도구 | 로그 | 상태 |
|---|---|---|
| **Claude Code** | `~/.claude/projects` | ✅ 지원 |
| **Codex** | `~/.codex` | ✅ 지원 |
| **Jan** | `<Jan data>/threads/*/messages.jsonl` | ✅ 지원 |
| Cursor | `state.vscdb` (SQLite) | 🚧 로드맵(로컬 로그에 타임스탬프가 적음) |
| Antigravity | `~/.gemini/antigravity/…` | 🚧 IDE 로그 암호화 — 조사 중 |

`--tools`로 도구 선택(예: `--tools claude jan`), `--tool-roots tool:/path`로 커스텀 경로 지정. 도구 추가는 작은 어댑터 하나(`scripts/wami/adapters/`)면 됩니다.

## 🤝 연결

[GitHub @shryu1994](https://github.com/shryu1994) · [X / Twitter](https://x.com/shryu1994) · [sh-ryu.com](https://sh-ryu.com) · [Issues](https://github.com/shryu1994/promptprint/issues)

제 핵심 작업과 같은 원칙 위에 있습니다 — [**ProvenanceBench**](https://github.com/shryu1994/provenance-bench)와 [**cite-or-refuse**](https://github.com/shryu1994/cite-or-refuse): 믿는 게 아니라 검증할 수 있는 주장.

## 라이선스

MIT © 2026 shryu
