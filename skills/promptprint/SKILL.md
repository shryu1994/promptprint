---
name: promptprint
description: 내가 AI 코딩 에이전트(Claude Code·Codex)에게 던진 질문들을 100% 로컬에서 분석해, 질문하는 전문성이 시간에 따라 어떻게 성장했는지 리포트로 보여준다. "내 질문 분석", "질문 성장", "Promptprint", "나의 프롬프트 회고" 같은 요청에 사용.
---

# Promptprint

당신이 그동안 AI 코딩 에이전트에게 던진 **질문**을 분석해, "질문하는 전문성"이 어떻게 성장했는지 보여주는 스킬입니다. Spotify Wrapped를 음악 대신 질문으로 한다고 보면 됩니다.

**프라이버시:** 전 과정이 당신 컴퓨터 안에서 끝납니다. 로그를 외부로 보내지 않으며, 분석은 이미 켜져 있는 호스트 에이전트(지금 이 LLM)가 수행합니다. 중간 산출물(`aggregates.json`, `insights.json`, 리포트)은 실제 질문을 담으므로 **절대 커밋하지 마세요**.

> 아래 명령은 번들 스크립트를 플러그인 설치 위치(`${CLAUDE_PLUGIN_ROOT}`)에서 실행하고, 산출물은 사용자의 현재 작업 디렉토리(`$PWD`)에 만듭니다.

## 절차

1. **결정적 집계** — 로그를 읽어 통계를 뽑습니다(LLM이 아니라 스크립트가, 매번 동일하게):
   ```bash
   PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 -m wami.cli aggregate --out "$PWD/aggregates.json"
   ```
   특정 도구만 보려면 `--claude <경로...>` / `--codex <경로...>`를 주고, 생략하면 기본 경로(`~/.claude/projects`, `~/.codex`)를 씁니다.

2. **`$PWD/aggregates.json`을 읽습니다.** 8개 섹션(`meta, activity, shape, topics, metaskill, mastery, tool_compare, samples`)이 있습니다. **수만 개 질문 전수가 아니라**, `samples.stratified`(대표 질문)와 집계 수치만 근거로 삼으세요. 그게 이 도구의 설계입니다(컨텍스트·비용 절약).

3. **6개 차원을 해석해 `$PWD/insights.json`을 만듭니다.** (아래 "6차원 해석 가이드"와 "출력 스키마"를 따르세요.)

4. **구조를 검증합니다:**
   ```bash
   PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 -m wami.cli validate-insights "$PWD/insights.json"
   ```
   실패하면 메시지를 보고 고쳐서 통과시키세요.

5. **리포트를 렌더합니다:**
   ```bash
   PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 -m wami.cli render \
     --insights "$PWD/insights.json" --aggregates "$PWD/aggregates.json" \
     --out "$PWD/promptprint-report.html"
   ```
   완료되면 사용자에게 `promptprint-report.html`을 브라우저로 열어 보라고 안내합니다. 공유 카드는 리포트 안의 "이미지로 저장" 버튼으로 내려받습니다.

## 6차원 해석 가이드

각 차원은 `dimensions.<key>`에 `{ "narrative": 한두 문단, "evidence": [실제 수치/인용 1개 이상] }`로 씁니다.

- **`topic_evolution` (주제의 진화):** `topics.term_timeline`과 `mastery`로 "무엇에 대해 묻는가"가 시간에 따라 어떻게 이동·심화했는지. evidence에 월별 등장 수치를 인용.
- **`depth` (질문의 깊이, how→why):** `samples.stratified`의 질문들을 직접 읽어 절차형("how")과 원리·트레이드오프형("why")으로 분류하고, `shape.avg_len_by_month` 추세와 결합. evidence에 실제 질문을 짧게 인용하고 길이 추세 수치를 넣으세요.
- **`metaskill` (AI를 다루는 성숙도):** `metaskill.totals`/`by_month`의 네 신호(critique 비판요청, verify 검증요구, delegate 위임, counter 역질문) 추세. evidence에 수치. 데이터가 적으면 과장하지 말 것.
- **`craft` (질문의 정교함):** `shape`의 코드블록 포함률·멀티스텝 비율·길이 분포 추세. evidence에 수치.
- **`mastery` (숙달, 반복→독립):** `mastery.topic_lifespan`에서 일찍 집중 등장했다가 사라진(졸업) 주제. evidence에 first/last 월.
- **`clusters` (당신만의 국면):** `topics.top_terms`를 의미 그룹으로 묶어 당신만의 작업 국면을 명명. evidence에 대표 term들.

## 다음 항로 (next_bearings) — 미래 처방

회고에 그치지 말고, 데이터에서 찾은 **약점·기회**를 바탕으로 2~4개의 구체적 개선 제안을 만듭니다. 각 제안은 `{title, why, how}`:
- `why`: 반드시 **지표/패턴에 정박**(예: "코드블록 동반률 7%로 낮음", "kubernetes가 6월에야 등장"). 근거 없는 일반론 금지.
- `how`: 구체적이고 실행 가능한 행동(막연한 "더 깊게 질문하세요"가 아니라).
- **단정 아닌 제안 톤.** 데이터가 빈약하면 신중히, 억지 제안 금지.
- 약점(낮은 차원)과 기회(새 주제·다음 단계) 양쪽에서 뽑되, 잔소리가 되지 않게 2~4개로 압축.

## 정박 규칙 (중요)

- 모든 `narrative`는 추측이 아니라 **집계 수치/샘플에 근거**해야 합니다. 통계 뼈대는 이미 결정적이니, 당신은 그 위에 해석·서사만 얹습니다.
- 각 차원의 `evidence`에는 **실제 숫자나 짧은 인용**이 1개 이상 들어가야 합니다.
- 데이터가 빈약한 차원은 부풀리지 말고 "데이터가 적어 신중히 본다"고 솔직히 쓰세요. 신뢰성이 이 도구의 핵심입니다.
- 노이즈 주의: 로그에는 IDE 컨텍스트·시스템 주입이 섞일 수 있습니다. `samples`에 그런 흔적(예: `# Context from my IDE setup`)이 보이면 해석에서 제외하고, 짧은 관측 기간이라면 최근 급증을 과대평가하지 마세요.
- **데이터 신뢰도 존중:** `aggregates.meta.confidence_tier`가 `snapshot`/`partial`이면 성장을 단정하지 말고 신중히 서술하라. `summary`에 한계를 명시하라(예: "기간이 짧거나 한 달에 집중되어 추세는 잠정적"). `full`이 아니면 과장 금지.
- **언어:** 사용자의 언어로 모든 콘텐츠(headline·summary·narrative·cards·next_bearings)를 작성하고, insights 최상위에 `"lang"` 코드(`"ko"`/`"en"` 등)를 넣어라 — 렌더가 고정 UI 라벨을 그 언어로 맞춘다.

## 톤

분석적이되 격려하는 **회고**의 톤. 독자(당신)에게 1인칭("당신")으로 말합니다. `cards`의 문구는 SNS에 공유할 만큼 짧고 임팩트 있게(큰 숫자 + 한 줄).

## 출력 스키마 (`insights.json`)

```jsonc
{
  "schema_version": "1",                  // 고정 "1"
  "lang": "ko",                            // 사용자 언어 코드(ko/en 등) — 렌더 UI 라벨용
  "headline": "...",                       // 한 줄 성장 요약(비어있지 않게)
  "summary": "...",                        // 1~2문단 종합 서사
  "dimensions": {                          // 정확히 아래 6개 키만
    "topic_evolution": { "narrative": "...", "evidence": ["...", "..."] },
    "depth":           { "narrative": "...", "evidence": ["..."] },
    "metaskill":       { "narrative": "...", "evidence": ["..."] },
    "craft":           { "narrative": "...", "evidence": ["..."] },
    "mastery":         { "narrative": "...", "evidence": ["..."] },
    "clusters":        { "narrative": "...", "evidence": ["..."] }
  },
  "chapters": [                            // 1개 이상, 시간순 내러티브(리포트용)
    { "title": "...", "period": "2026-04 ~ 2026-05", "narrative": "..." }
  ],
  "cards": [                               // 3~5개, Wrapped 공유카드용
    { "headline": "큰 숫자/한마디", "stat": "무엇인지", "caption": "맥락 한 줄" }
  ],
  "next_bearings": [                       // 2~4개, 데이터 정박 개선 제안
    { "title": "제안 제목", "why": "근거(지표/패턴 인용)", "how": "구체적 행동" }
  ]
}
```

규칙: `dimensions`는 위 6개 키만(추가/누락 불가). 각 dimension은 비어있지 않은 `narrative` + 1개 이상의 비어있지 않은 `evidence`. `chapters`는 1개 이상. `cards`는 3~5개. `next_bearings`는 2~4개(각 `title`·`why`·`how` 모두 비어있지 않게).

## 민감정보 주의

`aggregates.json`·`insights.json`·리포트는 실제 질문을 포함합니다. 커밋하지 마세요. 카드·리포트를 공유하기 전에 사용자가 내용을 직접 검토하도록 안내하세요.
