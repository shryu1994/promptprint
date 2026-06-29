---
name: promptprint
description: >-
  Analyze the questions you've asked your AI coding agents (Claude Code, Codex)
  100% locally and show how your questioning skill has grown over time, as a
  shareable report. Use for requests like 'analyze my questions', 'how my
  prompting grew', 'Promptprint', or 'my prompt retrospective'.
---

# Promptprint

당신이 그동안 AI 코딩 에이전트에게 던진 **질문**을 분석해, "질문하는 전문성"이 어떻게 성장했는지 보여주는 스킬입니다. Spotify Wrapped를 음악 대신 질문으로 한다고 보면 됩니다.

**프라이버시:** 전 과정이 당신 컴퓨터 안에서 끝납니다. 로그를 외부로 보내지 않으며, 분석은 이미 켜져 있는 호스트 에이전트(지금 이 LLM)가 수행합니다. 중간 산출물(`aggregates.json`, `insights.json`, 리포트)은 실제 질문을 담으므로 **절대 커밋하지 마세요**.

> 아래 명령은 번들 스크립트를 플러그인 설치 위치(`${CLAUDE_PLUGIN_ROOT}`)에서 실행하고, 산출물은 사용자의 현재 작업 디렉토리(`$PWD`)에 만듭니다.

## 절차

0. **대상(템플릿) 선택** — 누구에게 보여줄 리포트인지 사용자에게 먼저 묻고, 그 값(`personal`/`corporate`/`social`)을 **집계·렌더 양쪽에 동일하게** 넘깁니다. 템플릿이 데이터 정제 수준까지 결정합니다:
   - `personal` (개인 확인용): 전체 — 원문·프로젝트명 그대로.
   - `corporate` (사내 보고용): **원문 질문 제거 + 프로젝트명 익명화** — 성장 지표·추세만 남겨 사내 공유에 안전.
   - `social` (SNS 공유용): 카드 중심, 식별정보 0.

1. **결정적 집계** — 로그를 읽어 통계를 뽑습니다(LLM이 아니라 스크립트가, 매번 동일하게). `--template`에 0단계 값을 넣으세요 — **corporate/social이면 여기서 원문이 제거돼 LLM도 원문을 보지 않습니다**(프라이버시가 집계 단계에서 강제됨):
   ```bash
   PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 -m wami.cli aggregate --template personal --out "$PWD/aggregates.json"
   ```
   특정 도구만 보려면 `--tools claude codex`처럼 선택하고(생략 시 전체), 커스텀 경로는 `--claude <경로...>`/`--codex <경로...>`로 지정합니다. 기본 경로는 `~/.claude/projects`·`~/.codex`.

2. **`$PWD/aggregates.json`을 읽습니다.** 9개 섹션(`meta, activity, shape, topics, metaskill, mastery, skill_candidates, tool_compare, samples`)이 있습니다. **수만 개 질문 전수가 아니라**, `samples.stratified`(대표 질문)와 집계 수치만 근거로 삼으세요. 그게 이 도구의 설계입니다(컨텍스트·비용 절약).

3. **6개 차원을 해석해 `$PWD/insights.json`을 만듭니다.** (아래 "6차원 해석 가이드"와 "출력 스키마"를 따르세요.)
   - ⚠️ **corporate/social이면 evidence·narrative에 원문 질문을 인용하지 마세요 — 지표·추세만.** (집계가 이미 원문을 제거했고, 렌더가 인용을 한 번 더 걸러냅니다.) 이때 `depth`는 질문 인용 대신 `shape.avg_len_by_month`·코드블록률 같은 구조 지표로 해석합니다.

4. **구조를 검증합니다:**
   ```bash
   PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 -m wami.cli validate-insights "$PWD/insights.json"
   ```
   실패하면 메시지를 보고 고쳐서 통과시키세요.

5. **리포트를 렌더합니다:**
   ```bash
   PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 -m wami.cli render --template personal \
     --insights "$PWD/insights.json" --aggregates "$PWD/aggregates.json" \
     --out "$PWD/promptprint-report.html"
   ```
   **집계와 동일한 `--template`을 쓰세요.** social은 카드 중심으로, corporate는 원문 인용 없이 렌더됩니다(불일치 시 경고).
   완료되면 사용자에게 `promptprint-report.html`을 브라우저로 열어 보라고 안내합니다. 공유 카드는 리포트 안의 "이미지로 저장" 버튼으로 내려받습니다.

## 수시 점검 (delta) — 재실행용 짧은 모드

"요즘 어떻게 달라졌어?" · "promptprint check" 류의 *재실행* 요청이면, 연 1회 회고(위 6차원 전체) 대신 **최근 N일 vs 그 전 N일** 변화만 빠르게 보여줍니다(가벼운 대화형, 큰 HTML 리포트 없이). 회고가 1회용으로 끝나지 않게 하는 *수시·처방* 모드입니다.

1. 델타 계산(결정적, LLM 아님):
   ```bash
   PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/scripts" python3 -m wami.cli delta --window 30 --out "$PWD/delta.json"
   ```
   윈도우는 `--window 14`처럼 조절. 기준일은 마지막 로그 날짜 자동(`--as-of`로 고정 가능).

2. `$PWD/delta.json`을 읽고, **변한 것 + 처방을 앞세워** 짧게 서술합니다(회고 아님, *코치* 톤):
   - **무엇이 움직였나(길이에 강건):** `deltas.metaskill_rate`(verify·critique·delegate·counter, per-message 비율 변화 pp)와 `deltas.code_block_rate`·`deltas.q_per_session`·`deltas.one_shot_rate`(원샷=한 번에 끝낸 세션 비율, 세션당 왕복수와 짝). **"verify가 +18%p"처럼 *비율*로 말하고, 질문 수 폭증(`deltas.total`)으로 성장을 단정하지 마라 — 비율이 진짜 신호다.** ⚠️ 왕복수↓·원샷률↑이 늘 "좋아짐"은 아니다(복잡한 작업은 본래 왕복이 많다) — 추세로만 말하고 단정 금지.
   - **다음에 뭘 할까(처방, 헤드라인):** `skill_candidates`(최근 반복·재설명 노역)에서 1~2개 → "X를 N번 재설명 중 → `/skill-creator`로 스킬화"처럼 *데이터 정박·실행가능*하게. 처방을 앞에, 회고는 곁가지.
   - **새/사라진 관심:** `new_topics`·`dropped_topics` 한 줄.
   - ⚠️ `recent.total`·`prior.total`이 크게 불균형이면(휴지기/폭증) 비율만 신뢰하고 절대수 비교는 신중히. 데이터 적으면 과장 금지(신뢰성이 이 도구의 핵심).
   - 사용자 언어로. "지난 N일 동안 너는 ~를 더/덜 했고, 다음 한 가지는 ~." 한 화면에 끝나게.

## 6차원 해석 가이드

각 차원은 `dimensions.<key>`에 `{ "narrative": 한두 문단, "evidence": [실제 수치/인용 1개 이상] }`로 씁니다.

- **`topic_evolution` (주제의 진화):** `topics.term_timeline`과 `mastery`로 "무엇에 대해 묻는가"가 시간에 따라 어떻게 이동·심화했는지. evidence에 월별 등장 수치를 인용.
- **`depth` (질문의 깊이, how→why):** `samples.stratified`의 질문들을 직접 읽어 절차형("how")과 원리·트레이드오프형("why")으로 분류하고, `shape.avg_len_by_month` 추세와 결합. evidence에 실제 질문을 짧게 인용하고 길이 추세 수치를 넣으세요.
- **`metaskill` (AI를 다루는 성숙도):** **`metaskill.totals_msgs`/`by_month_msgs`(신호가 1회+ 등장한 질문 수, 0/1)를 1차 지표로** 네 신호(critique 비판요청, verify 검증요구, delegate 위임, counter 역질문) 추세를 본다 — "받아쓰기 → 지휘·검증" 성숙도. ⚠️ `totals`/`by_month`는 매치 '횟수'라 프롬프트가 길수록 부풀려진다(길이 교란) — 보조로만 쓰고, verify 급증이 보이면 `shape.avg_len_by_month` 추세와 분리해 "정말 더 검증했나, 단지 길어졌나"를 구분하라. evidence에 수치, 데이터 적으면 과장 금지.
- **`craft` (질문의 정교함):** `shape`의 코드블록 포함률·멀티스텝 비율·길이 분포 추세. evidence에 수치.
- **`mastery` (숙달, 반복→독립):** `mastery.topic_lifespan`에서 일찍 집중 등장했다가 사라진(졸업) 주제. evidence에 first/last 월.
- **`clusters` (당신만의 국면):** `topics.top_terms`를 의미 그룹으로 묶어 당신만의 작업 국면을 명명. 각 term의 `project_count`가 작을수록(= 적은 프로젝트에 집중) 진짜 주제일 확률이 높다 — 모든 프로젝트에 두루 나오는 일반어보다 우선해 묶어라. evidence에 대표 term들.

## 다음 항로 (next_bearings) — 미래 처방

회고에 그치지 말고, 데이터에서 찾은 **약점·기회**를 바탕으로 2~4개의 구체적 개선 제안을 만듭니다. 각 제안은 `{title, why, how}`:
- `why`: 반드시 **지표/패턴에 정박**(예: "코드블록 동반률 7%로 낮음", "kubernetes가 6월에야 등장"). 근거 없는 일반론 금지.
- `how`: 구체적이고 실행 가능한 행동(막연한 "더 깊게 질문하세요"가 아니라).
- **단정 아닌 제안 톤.** 데이터가 빈약하면 신중히, 억지 제안 금지.
- 약점(낮은 차원)과 기회(새 주제·다음 단계) 양쪽에서 뽑되, 잔소리가 되지 않게 2~4개로 압축.

## 스킬 제안 (skill_suggestions) — 행동: "더 묻지 말고 스킬로 만들어라" (선택)

회고(과거 분석)·처방(다음 항로) 다음의 마지막 조각 — **반복·재설명하는 작업을 `/skill-creator`로 스킬화**하라고 제안해 루프를 닫습니다. `aggregates.skill_candidates.candidates`(L3가 결정적으로 탐지한 상위 후보)를 읽어 **0~3개**를 만듭니다. 각 항목 = `{name, why, evidence, est_savings?, seed}`:

- 후보 = **반복은 많은데 졸업하지 않고(계속 재등장) 매번 같은 맥락을 재설명**하는 term. 근거 필드: `count`(반복), `avg_len`(재설명 비용 = 스킬화 ROI 핵심), `months_active`(지속), `recent_count`(최근성).
- **학습 중(곧 졸업할 주제)과 반복 노역을 구분**하라 — L3가 졸업 term은 이미 뺐지만, 빈약한 데이터면 무리하지 말고 **0개로 두라**(억지 제안 금지). `confidence_tier`가 `snapshot`이면 특히 보수적으로.
- 같은 프롬프트에 공기하는 여러 term은 **하나의 작업으로 묶어** 명명하라(L3는 단일 term 단위라 동점이 생긴다).
- `name`: 만들 스킬의 짧은 이름. `why`: **실측 수치에 정박**(예: "deploy를 4회 반복, 평균 143자로 매번 맥락 재설정"). `evidence`: candidate의 측정값(count·avg_len·months) 인용.
- `est_savings`(선택): **반드시 추정으로 명시 + 가정 노출**(예: "추정: 회당 ~140자 재설명 제거 × 4회 · 가정 — 질문당 1회 호출로 대체"). **조작된 ROI 금지** — 실측 N·M에만 정박하고 추정은 추정이라고 밝혀라(피드백 #1의 교훈: 과장 지표 금지).
- `seed`: 바로 `/skill-creator`에 넣을 한 단락 — 스킬의 목적·입력·출력 + `samples.stratified`에서 고른 대표 예시 2~3개.
- ⚠️ **corporate/social이면 `seed`·`why`·`evidence`에 원문 질문을 인용하지 마라** — 작업을 추상적으로 기술(집계가 이미 원문을 제거했고 렌더가 인용을 한 번 더 거른다). **corporate에서는 이 섹션이 헤드라인(팀 능률 ROI)** 이니 절감 추정을 앞세우되 정직하게.

## 정박 규칙 (중요)

- 모든 `narrative`는 추측이 아니라 **집계 수치/샘플에 근거**해야 합니다. 통계 뼈대는 이미 결정적이니, 당신은 그 위에 해석·서사만 얹습니다.
- 각 차원의 `evidence`에는 **실제 숫자나 짧은 인용**이 1개 이상 들어가야 합니다.
- 데이터가 빈약한 차원은 부풀리지 말고 "데이터가 적어 신중히 본다"고 솔직히 쓰세요. 신뢰성이 이 도구의 핵심입니다.
- 노이즈 주의: 로그에는 IDE 컨텍스트·시스템 주입이 섞일 수 있습니다. `samples`에 그런 흔적(예: `# Context from my IDE setup`)이 보이면 해석에서 제외하고, 짧은 관측 기간이라면 최근 급증을 과대평가하지 마세요.
- **데이터 신뢰도 존중:** `aggregates.meta.confidence_tier`가 `snapshot`/`partial`이면 성장을 단정하지 말고 신중히 서술하라. `summary`에 한계를 명시하라(예: "기간이 짧거나 한 달에 집중되어 추세는 잠정적"). `full`이 아니면 과장 금지.
- **언어:** 사용자의 언어로 모든 콘텐츠(headline·summary·narrative·cards·next_bearings)를 작성하고, insights 최상위에 `"lang"` 코드(`"ko"`/`"en"` 등)를 넣어라 — 렌더가 고정 UI 라벨을 그 언어로 맞춘다.

## 톤

분석적이되 격려하는 **회고**의 톤. 독자(당신)에게 1인칭("당신")으로 말합니다. `cards`의 문구는 SNS에 공유할 만큼 짧고 임팩트 있게 — 단 **헤드라인은 길이에 강건한 *비율/변화*로**(바로 아래 "공유 카드" 규칙). 원시 횟수·"평균 길이 N배"는 금지.

## 공유 카드 (cards) — 길이에 강건한 지표만

카드는 SNS에 공유되니 *오해 없이* 자랑할 수 있어야 한다. **헤드라인은 길이에 강건한 *비율* 또는 *비율 변화*로 써라 — 원시 횟수나 "평균 길이가 N배"는 금지.**

- ✅ 좋은 예: "코드 동반률 7% → 24%", "검증 질문 비율 2배(전체의 8%→17%)", "한 세션당 묻는 횟수 3.1 → 1.9(왕복 감소)".
- ❌ 나쁜 예: "검증 7,458회"(맥락 없는 큰 수·길이 교란), **"질문이 10배 길어짐"** — *길이 증가는 정교함이 아니라 비대로 읽혀 오히려 나빠 보인다.* 도구 방법론 자체가 길이를 불신한다(metaskill `totals`는 길이 교란, `totals_msgs`가 1차).
- **근거 산출:** `shape`(코드블록 포함률·멀티스텝 비율·길이 분포)와 `metaskill.totals_msgs`/`by_month_msgs`(per-message 비율)에서 *비율*을 계산해 쓰고, 가능하면 초기 월 → 최근 월 *변화*로 보여라. 절대수가 필요하면 caption에 보조로만.
- 데이터가 적으면(`confidence_tier` snapshot/partial) 카드도 신중히 — 억지 헤드라인·과장 금지.
- **장르 믹스 카드(공유성 높음):** `genre_mix.mix`(디버그·구현·이해·개선·기타 분포, heuristic v1)로 "내 질문의 결" 카드를 만들 수 있다 — 단 *분류는 휴리스틱*이니 "구현 42%·디버그 23%"처럼 *분포*로만, "너는 디버거다" 같은 단정 금지. `genre_mix.by_month`로 결의 *변화*(예: 구현→이해 이동)를 보여주면 더 좋다.
- 카드엔 **지표·주제 라벨만, 원문 질문 절대 금지**(렌더가 한 번 더 거르지만 작성 단계부터 넣지 마라).

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
    { "headline": "길이보정 비율/변화 (예: 코드 동반률 7%→24%) — 원시 횟수·평균길이 금지", "stat": "무엇인지", "caption": "맥락 한 줄" }
  ],
  "next_bearings": [                       // 2~4개, 데이터 정박 개선 제안
    { "title": "제안 제목", "why": "근거(지표/패턴 인용)", "how": "구체적 행동" }
  ],
  "skill_suggestions": [                    // 선택, 0~3개 — 반복 작업의 스킬화 제안(기둥3)
    { "name": "스킬 이름", "why": "실측 정박", "evidence": ["count=4 · avg_len=143자 …"],
      "est_savings": "추정 … (가정 노출)", "seed": "/skill-creator 에 넣을 한 단락" }
  ]
}
```

규칙: `dimensions`는 위 6개 키만(추가/누락 불가). 각 dimension은 비어있지 않은 `narrative` + 1개 이상의 비어있지 않은 `evidence`. `chapters`는 1개 이상. `cards`는 3~5개. `next_bearings`는 2~4개(각 `title`·`why`·`how` 모두 비어있지 않게). `skill_suggestions`는 **선택(0~3개)** — 있으면 각 `name`·`why`·`seed`는 비어있지 않게, `evidence`는 1개 이상, `est_savings`는 있으면 비어있지 않게.

## 민감정보 주의

`aggregates.json`·`insights.json`·리포트는 실제 질문을 포함합니다. 커밋하지 마세요. 카드·리포트를 공유하기 전에 사용자가 내용을 직접 검토하도록 안내하세요.
