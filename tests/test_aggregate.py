import json
import unittest
import tests.conftest_path  # noqa: F401
from wami.model import QuestionRecord
from wami.aggregate import build_aggregates


def mk(ts, tool, text, sid="s", proj="p", turn=0):
    return QuestionRecord(ts=ts, tool=tool, session_id=sid, project=proj, text=text, turn_idx=turn)


RECS = [
    mk("2026-01-05T10:00:00+00:00", "claude", "how do I cache results?", sid="s1", turn=0),
    mk("2026-01-05T10:01:00+00:00", "claude", "why is it faster?\n```py\nx=1\n```", sid="s1", turn=1),
    mk("2026-02-10T09:00:00+00:00", "codex",  "1. setup\n2. run\n3. verify it works", sid="s2", turn=0),
]


class AggregateMetaTest(unittest.TestCase):
    def setUp(self):
        self.agg = build_aggregates(RECS)

    def test_meta_counts(self):
        self.assertEqual(self.agg["meta"]["total_questions"], 3)
        self.assertEqual(self.agg["meta"]["by_tool"], {"claude": 2, "codex": 1})
        self.assertEqual(self.agg["meta"]["date_range"],
                         ["2026-01-05T10:00:00+00:00", "2026-02-10T09:00:00+00:00"])

    def test_activity_by_month(self):
        self.assertEqual(self.agg["activity"]["by_month"], {"2026-01": 2, "2026-02": 1})

    def test_shape_code_and_multistep(self):
        self.assertEqual(self.agg["shape"]["code_block_count"], 1)
        self.assertEqual(self.agg["shape"]["multistep_count"], 1)
        self.assertEqual(self.agg["shape"]["total"], 3)
        # 길이 버킷: 키 존재 확인
        self.assertIn("length_buckets", self.agg["shape"])

    def test_shape_exact_values(self):
        # All three RECS texts are < 60 chars (lens: 23, 31, 34)
        self.assertEqual(self.agg["shape"]["length_buckets"], {"xs": 3})
        # avg_len_by_month: 2026-01 has (23+31)/2=27.0; 2026-02 has 34/1=34.0
        self.assertEqual(
            self.agg["shape"]["avg_len_by_month"],
            {"2026-01": 27.0, "2026-02": 34.0},
        )

    def test_activity_by_hour_exact(self):
        # RECS hours: "10", "10", "09"
        self.assertEqual(
            self.agg["activity"]["by_hour"],
            {"09": 1, "10": 2},
        )


class AggregateTopicsTest(unittest.TestCase):
    def setUp(self):
        self.agg = build_aggregates(RECS)

    def test_top_terms_present(self):
        topics = self.agg["topics"]
        terms = {x["term"]: x["count"] for x in topics["top_terms"]}
        # "cache"는 RECS[0]에 등장
        self.assertIn("cache", terms)
        self.assertGreaterEqual(terms["cache"], 1)

    def test_term_timeline_cache_exact(self):
        # "cache" appears once in RECS[0], month 2026-01
        self.assertEqual(
            self.agg["topics"]["term_timeline"]["cache"],
            {"2026-01": 1},
        )

    def test_term_timeline_shape(self):
        tl = self.agg["topics"]["term_timeline"]
        # 상위 term 각각에 대해 {month: count}
        for term, months in tl.items():
            self.assertIsInstance(months, dict)


class AggregateMetaskillTest(unittest.TestCase):
    def test_signals_counted(self):
        recs = [
            mk("2026-01-01T00:00:00+00:00", "claude", "이거 비판해줘", sid="a"),
            mk("2026-01-02T00:00:00+00:00", "claude", "정말 맞는지 검증해줘", sid="a", turn=1),
        ]
        agg = build_aggregates(recs)
        ms = agg["metaskill"]
        self.assertGreaterEqual(ms["totals"]["critique"], 1)
        self.assertGreaterEqual(ms["totals"]["verify"], 1)
        self.assertIn("2026-01", ms["by_month"])

    def test_msgs_vs_counts_deconfounds_length(self):
        # 한 메시지에 verify 신호 3회 → totals(매치수)는 ≥3, totals_msgs(메시지수)는 1.
        recs = [mk("2026-01-01T00:00:00+00:00", "claude",
                   "이거 검증하고 저거 검증하고 또 검증해줘", sid="a")]
        ms = build_aggregates(recs)["metaskill"]
        self.assertGreaterEqual(ms["totals"]["verify"], 3)      # 매치 횟수 합
        self.assertEqual(ms["totals_msgs"]["verify"], 1)         # 신호가 뜬 메시지 수
        self.assertEqual(ms["by_month_msgs"]["2026-01"]["verify"], 1)


class AggregateTopicSpecificityTest(unittest.TestCase):
    def test_concentrated_term_outranks_ubiquitous(self):
        # 'common'은 3개 프로젝트에 두루(count 3), 'gcp'는 1개 프로젝트에 집중(count 3).
        # 동일 빈도라도 프로젝트 집중도가 높은 'gcp'가 상위여야 한다.
        recs = []
        for i, proj in enumerate(["p1", "p2", "p3"]):
            recs.append(mk(f"2026-0{i + 1}-01T00:00:00+00:00", "claude",
                           "common topic here", proj=proj, sid=proj))
        for i in range(3):
            recs.append(mk(f"2026-0{i + 1}-15T00:00:00+00:00", "claude",
                           "gcp deployment guide", proj="p1", sid=f"g{i}"))
        agg = build_aggregates(recs)
        order = [x["term"] for x in agg["topics"]["top_terms"]]
        tt = {x["term"]: x for x in agg["topics"]["top_terms"]}
        self.assertIn("gcp", order)
        self.assertIn("common", order)
        self.assertLess(order.index("gcp"), order.index("common"))
        self.assertEqual(tt["gcp"]["project_count"], 1)
        self.assertEqual(tt["common"]["project_count"], 3)


class AggregateEmptyTest(unittest.TestCase):
    def test_empty_records(self):
        agg = build_aggregates([])
        for section in ("meta", "activity", "shape", "topics", "metaskill", "mastery",
                        "session_shape", "tool_compare", "samples"):
            self.assertIn(section, agg)
        self.assertEqual(agg["meta"]["total_questions"], 0)
        self.assertEqual(agg["meta"]["date_range"], [None, None])


class AggregateSessionShapeTest(unittest.TestCase):
    """세션모양 — 세션당 왕복수(질문 수) + 원샷 비율. '바꿀 수 있는' 행동 지표."""

    SHAPE_KEYS = {"sessions", "questions_per_session", "one_shot_sessions",
                  "one_shot_rate", "size_buckets", "by_month"}

    def _recs(self):
        # s1: 3질문(2026-01), s2: 1질문 원샷(2026-01), s3: 1질문 원샷(2026-02)
        return [
            mk("2026-01-05T10:00:00+00:00", "claude", "q a", sid="s1", turn=0),
            mk("2026-01-05T10:01:00+00:00", "claude", "q b", sid="s1", turn=1),
            mk("2026-01-05T10:02:00+00:00", "claude", "q c", sid="s1", turn=2),
            mk("2026-01-20T09:00:00+00:00", "codex",  "q d", sid="s2", turn=0),
            mk("2026-02-10T09:00:00+00:00", "codex",  "q e", sid="s3", turn=0),
        ]

    def setUp(self):
        self.ss = build_aggregates(self._recs())["session_shape"]

    def test_shape_keys(self):
        self.assertEqual(set(self.ss.keys()), self.SHAPE_KEYS)

    def test_counts_and_rates(self):
        # 3 세션, 5 질문 → 5/3 = 1.67; 원샷 2개(s2,s3) → 2/3 = 0.667
        self.assertEqual(self.ss["sessions"], 3)
        self.assertEqual(self.ss["questions_per_session"], 1.67)
        self.assertEqual(self.ss["one_shot_sessions"], 2)
        self.assertEqual(self.ss["one_shot_rate"], 0.667)

    def test_size_buckets(self):
        # s1=3질문→"2-3", s2·s3=1질문→"1"
        self.assertEqual(self.ss["size_buckets"], {"1": 2, "2-3": 1})

    def test_by_month_uses_first_question_month(self):
        # 2026-01: s1(3q)+s2(1q)=2세션/4질문, 원샷1 → q_per_session 2.0, one_shot_rate 0.5
        # 2026-02: s3(1q)=1세션/1질문, 원샷1 → q_per_session 1.0, one_shot_rate 1.0
        self.assertEqual(self.ss["by_month"]["2026-01"],
                         {"sessions": 2, "questions_per_session": 2.0, "one_shot_rate": 0.5})
        self.assertEqual(self.ss["by_month"]["2026-02"],
                         {"sessions": 1, "questions_per_session": 1.0, "one_shot_rate": 1.0})

    def test_deterministic(self):
        ss2 = build_aggregates(self._recs())["session_shape"]
        self.assertEqual(self.ss, ss2)

    def test_empty_records(self):
        ss = build_aggregates([])["session_shape"]
        self.assertEqual(ss["sessions"], 0)
        self.assertEqual(ss["questions_per_session"], 0.0)
        self.assertEqual(ss["one_shot_sessions"], 0)
        self.assertEqual(ss["one_shot_rate"], 0.0)
        self.assertEqual(ss["size_buckets"], {})
        self.assertEqual(ss["by_month"], {})

    def test_big_session_bucket(self):
        recs = [mk(f"2026-03-01T{i:02d}:00:00+00:00", "claude", "x", sid="big", turn=i)
                for i in range(9)]
        ss = build_aggregates(recs)["session_shape"]
        self.assertEqual(ss["size_buckets"], {"8+": 1})
        self.assertEqual(ss["one_shot_rate"], 0.0)


class AggregateConfidenceTierTest(unittest.TestCase):
    """_confidence_tier 규칙의 결정적 동작을 검증한다."""

    def _make_recs(self, months_and_counts):
        """{'YYYY-MM': n} 형태로 레코드를 생성하는 헬퍼."""
        recs = []
        for month, n in months_and_counts.items():
            for i in range(n):
                ts = f"{month}-01T{i:02d}:00:00+00:00"
                recs.append(mk(ts, "claude", "x" * 30, sid=month, turn=i))
        return recs

    def test_snapshot_thin_single_month(self):
        # total=3 (<100), active_months=1 (<2), max_month_ratio=1.0 (>0.7) → snapshot
        recs = self._make_recs({"2026-01": 3})
        agg = build_aggregates(recs)
        self.assertEqual(agg["meta"]["confidence_tier"], "snapshot")
        self.assertIsInstance(agg["meta"]["confidence_note"], str)
        self.assertGreater(len(agg["meta"]["confidence_note"]), 0)

    def test_snapshot_few_records_two_months(self):
        # total=10 (<100) → snapshot (total 조건만으로 충분)
        recs = self._make_recs({"2026-01": 5, "2026-02": 5})
        agg = build_aggregates(recs)
        self.assertEqual(agg["meta"]["confidence_tier"], "snapshot")

    def test_snapshot_dominated_single_month(self):
        # total=200, active_months=3 이지만 max_month_ratio=180/200=0.9 (>0.7) → snapshot
        recs = self._make_recs({"2026-01": 180, "2026-02": 10, "2026-03": 10})
        agg = build_aggregates(recs)
        self.assertEqual(agg["meta"]["confidence_tier"], "snapshot")

    def test_partial_mid_case(self):
        # total=200 (<500), active_months=4, max_month_ratio=0.25 (≤0.5)
        # → partial (total 조건)
        recs = self._make_recs({"2026-01": 50, "2026-02": 50, "2026-03": 50, "2026-04": 50})
        agg = build_aggregates(recs)
        self.assertEqual(agg["meta"]["confidence_tier"], "partial")

    def test_partial_two_months_enough_total(self):
        # total=600 (≥500), active_months=2 (<3), max_month_ratio=0.5 (≤0.5)
        # → partial (active_months 조건)
        recs = self._make_recs({"2026-01": 300, "2026-02": 300})
        agg = build_aggregates(recs)
        self.assertEqual(agg["meta"]["confidence_tier"], "partial")

    def test_full_spread_plenty(self):
        # total=600 (≥500), active_months=6 (≥3), max_month_ratio=100/600≈0.167 (≤0.5)
        recs = self._make_recs({
            "2026-01": 100, "2026-02": 100, "2026-03": 100,
            "2026-04": 100, "2026-05": 100, "2026-06": 100,
        })
        agg = build_aggregates(recs)
        self.assertEqual(agg["meta"]["confidence_tier"], "full")
        self.assertIsInstance(agg["meta"]["confidence_note"], str)

    def test_deterministic(self):
        # 동일 입력에서 두 번 호출해도 결과가 같아야 한다.
        recs = self._make_recs({"2026-01": 50, "2026-02": 50, "2026-03": 50, "2026-04": 50})
        r1 = build_aggregates(recs)["meta"]["confidence_tier"]
        r2 = build_aggregates(recs)["meta"]["confidence_tier"]
        self.assertEqual(r1, r2)

    def test_existing_meta_keys_still_present(self):
        # 기존 키들이 confidence 키 추가 후에도 그대로 존재해야 한다.
        agg = build_aggregates(RECS)
        for key in ("total_questions", "by_tool", "date_range", "confidence_tier", "confidence_note"):
            self.assertIn(key, agg["meta"])


class AggregateMasterySamplesTest(unittest.TestCase):
    def setUp(self):
        recs = [
            mk("2026-01-01T00:00:00+00:00", "claude", "docker network bridge 설정", sid="a", turn=0),
            mk("2026-01-15T00:00:00+00:00", "claude", "docker network 다시 질문", sid="a", turn=1),
            mk("2026-03-01T00:00:00+00:00", "codex",  "kubernetes ingress 설정", sid="b", turn=0),
        ]
        self.agg = build_aggregates(recs)

    def test_mastery_lifespan(self):
        spans = {row["term"]: row for row in self.agg["mastery"]["topic_lifespan"]}
        self.assertIn("docker", spans)
        self.assertEqual(spans["docker"]["count"], 2)
        self.assertEqual(spans["docker"]["first"], "2026-01")
        self.assertEqual(spans["docker"]["last"], "2026-01")

    def test_tool_compare(self):
        tc = self.agg["tool_compare"]
        self.assertIn("claude", tc)
        self.assertIn("codex", tc)
        self.assertEqual(tc["claude"]["count"], 2)

    def test_stratified_samples_deterministic(self):
        s1 = self.agg["samples"]["stratified"]
        s2 = build_aggregates([
            mk("2026-01-01T00:00:00+00:00", "claude", "docker network bridge 설정", sid="a", turn=0),
            mk("2026-01-15T00:00:00+00:00", "claude", "docker network 다시 질문", sid="a", turn=1),
            mk("2026-03-01T00:00:00+00:00", "codex",  "kubernetes ingress 설정", sid="b", turn=0),
        ])["samples"]["stratified"]
        self.assertEqual(s1, s2)               # 결정적
        self.assertTrue(all("text" in x for x in s1))


class AggregateTemplateRedactionTest(unittest.TestCase):
    def _recs(self):
        return [
            mk("2026-01-05T10:00:00+00:00", "claude",
               "fix the bug in /Users/me/secret.py with token sk-abc123XYZ",
               proj="billing-svc", sid="s1"),
            mk("2026-02-05T10:00:00+00:00", "codex",
               "deploy the api-gateway service to prod",
               proj="api-gateway", sid="s2"),
        ]

    def test_personal_keeps_text_and_project(self):
        agg = build_aggregates(self._recs())  # 기본 personal
        self.assertEqual(agg["meta"]["template"], "personal")
        samp = agg["samples"]["stratified"]
        self.assertTrue(any("/Users/me/secret.py" in (s.get("text") or "") for s in samp))
        self.assertTrue(any(s.get("project") == "billing-svc" for s in samp))

    def test_corporate_redacts_text_and_anonymizes_project(self):
        agg = build_aggregates(self._recs(), template="corporate")
        self.assertEqual(agg["meta"]["template"], "corporate")
        blob = json.dumps(agg["samples"], ensure_ascii=False)
        # 민감 원문·경로·시크릿·실제 프로젝트명 0건
        for needle in ("/Users/me/secret.py", "sk-abc123XYZ", "billing-svc",
                       "api-gateway", "fix the bug", "deploy the"):
            self.assertNotIn(needle, blob, f"corporate 집계에 민감 데이터 잔존: {needle!r}")
        self.assertIn("project-", blob)  # 익명 라벨로 치환됨

    def test_social_also_redacts(self):
        agg = build_aggregates(self._recs(), template="social")
        blob = json.dumps(agg["samples"], ensure_ascii=False)
        self.assertNotIn("sk-abc123XYZ", blob)
        self.assertNotIn("billing-svc", blob)


class AggregateGenreMixTest(unittest.TestCase):
    """질문 장르 믹스 — '무엇을 묻는가' 택소노미(공유성 높음)."""

    def _recs(self):
        return [
            mk("2026-01-05T10:00:00+00:00", "claude", "how do I add a login button", sid="s1", turn=0),
            mk("2026-01-06T10:00:00+00:00", "claude", "로그인 기능 구현해줘", sid="s2", turn=0),
            mk("2026-01-07T10:00:00+00:00", "claude", "이거 왜 안 돼 에러 고쳐줘", sid="s3", turn=0),
            mk("2026-02-01T10:00:00+00:00", "codex",  "what is a closure", sid="s4", turn=0),
            mk("2026-02-02T10:00:00+00:00", "codex",  "ㅁㄴㅇㄹ", sid="s5", turn=0),
        ]

    def setUp(self):
        self.gm = build_aggregates(self._recs())["genre_mix"]
        self.by_genre = {m["genre"]: m for m in self.gm["mix"]}

    def test_section_keys(self):
        self.assertEqual(set(self.gm.keys()), {"total", "mix", "by_month"})

    def test_counts_and_rates(self):
        # build 2(button·구현), debug 1, understand 1, other 1
        self.assertEqual(self.gm["total"], 5)
        self.assertEqual(self.by_genre["build"]["count"], 2)
        self.assertEqual(self.by_genre["build"]["rate"], 0.4)
        self.assertEqual(self.by_genre["debug"]["count"], 1)
        self.assertEqual(self.by_genre["understand"]["count"], 1)
        self.assertEqual(self.by_genre["other"]["count"], 1)

    def test_mix_sorted_by_count_desc(self):
        counts = [m["count"] for m in self.gm["mix"]]
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(self.gm["mix"][0]["genre"], "build")  # 최다

    def test_rates_sum_to_one(self):
        self.assertAlmostEqual(sum(m["rate"] for m in self.gm["mix"]), 1.0, places=2)

    def test_by_month(self):
        self.assertEqual(self.gm["by_month"]["2026-01"], {"build": 2, "debug": 1})
        self.assertEqual(self.gm["by_month"]["2026-02"], {"understand": 1, "other": 1})

    def test_no_raw_text(self):
        # 장르 라벨+수치만 — 원문 0(corporate/social 안전).
        blob = json.dumps(self.gm, ensure_ascii=False)
        self.assertNotIn("login button", blob)
        self.assertNotIn("로그인", blob)

    def test_deterministic(self):
        gm2 = build_aggregates(self._recs())["genre_mix"]
        self.assertEqual(self.gm, gm2)

    def test_empty(self):
        gm = build_aggregates([])["genre_mix"]
        self.assertEqual(gm, {"total": 0, "mix": [], "by_month": {}})


class AggregateSkillCandidatesTest(unittest.TestCase):
    """기둥3: skill_candidates — 반복·비졸업·재설명비용 큰 작업의 결정적 탐지."""

    CAND_KEYS = {"term", "count", "avg_len", "months_active", "first", "last",
                 "recent_count", "project_count", "score"}

    def _recs(self):
        recs = []
        # "deploy": 4개 질문에 걸쳐 유일하게 반복되는 핵심어(count 4) + 매번 긴 맥락 재설명 → 후보.
        # (나머지 단어는 질문마다 달라 deploy 만 공통 — 단일 작업의 반복 재설명을 모사)
        deploy_qs = [
            "deploy the billing pipeline to staging — full env, secrets, and rollback context again",
            "deploy the analytics worker to prod with the same migration checklist as last time here",
            "deploy the gateway release, re-explaining the canary steps and health thresholds once more",
            "deploy hotfix now; here is the entire incident background and the on-call runbook restated",
        ]
        months = ["2026-04", "2026-05", "2026-06", "2026-06"]
        for i, (q, m) in enumerate(zip(deploy_qs, months)):
            recs.append(mk(f"{m}-1{i}T10:00:00+00:00", "claude", q, sid=f"d{i}", proj="svc", turn=i))
        # "docker": 초반(2026-01~02)에만 등장 후 사라짐(count 3) → 졸업 → 제외.
        for i, m in enumerate(["2026-01", "2026-01", "2026-02"]):
            recs.append(mk(f"{m}-05T0{i}:00:00+00:00", "claude", "docker setup question here", sid=f"k{i}", proj="old", turn=i))
        # "rareword": 1회 → MIN_COUNT 미만 → 제외.
        recs.append(mk("2026-06-01T09:00:00+00:00", "claude", "rareword oneoff thing", sid="r1", proj="svc", turn=0))
        return recs

    def setUp(self):
        self.agg = build_aggregates(self._recs())
        self.cands = self.agg["skill_candidates"]["candidates"]
        self.by_term = {c["term"]: c for c in self.cands}

    def test_section_present(self):
        self.assertIn("skill_candidates", self.agg)
        self.assertIsInstance(self.cands, list)

    def test_repeated_recurring_term_is_candidate(self):
        self.assertIn("deploy", self.by_term)
        self.assertEqual(self.by_term["deploy"]["count"], 4)
        self.assertGreater(self.by_term["deploy"]["avg_len"], 60)

    def test_graduated_term_excluded(self):
        # docker는 count>=3 이지만 최근 윈도(마지막 2개월) 밖에서 졸업 → 제외.
        self.assertNotIn("docker", self.by_term)

    def test_below_min_count_excluded(self):
        self.assertNotIn("rareword", self.by_term)

    def test_candidate_shape(self):
        for c in self.cands:
            self.assertEqual(set(c.keys()), self.CAND_KEYS)
            self.assertIsInstance(c["count"], int)
            self.assertIsInstance(c["avg_len"], float)
            self.assertIsInstance(c["months_active"], int)

    def test_top_n_bound(self):
        self.assertLessEqual(len(self.cands), 5)

    def test_sorted_by_score_desc(self):
        scores = [c["score"] for c in self.cands]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_deterministic(self):
        c2 = build_aggregates(self._recs())["skill_candidates"]["candidates"]
        self.assertEqual(self.cands, c2)

    def test_no_raw_text_or_project_names(self):
        # corporate 안전 by construction: term+수치만 — 원문 문장·프로젝트명 0.
        blob = json.dumps(self.agg["skill_candidates"], ensure_ascii=False)
        self.assertNotIn("deploy the billing pipeline", blob)  # 원문 문장
        self.assertNotIn("svc", blob)                          # 프로젝트명
        self.assertNotIn("old", blob)

    def test_empty_records(self):
        agg = build_aggregates([])
        self.assertEqual(agg["skill_candidates"]["candidates"], [])
