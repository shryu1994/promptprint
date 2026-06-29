import unittest
import tests.conftest_path  # noqa: F401
from wami import redact as R


FULL = {"hero", "chart", "chapters", "dims", "cards", "bearings", "skills"}


class SectionPolicyTest(unittest.TestCase):
    def test_personal_and_corporate_full(self):
        self.assertEqual(R.section_policy("personal"), FULL)
        self.assertEqual(R.section_policy("corporate"), FULL)

    def test_social_cards_only(self):
        self.assertEqual(R.section_policy("social"), {"hero", "cards"})

    def test_unknown_falls_back_to_personal(self):
        self.assertEqual(R.section_policy("bogus"), FULL)


class IsRedactedTest(unittest.TestCase):
    def test_levels(self):
        self.assertFalse(R.is_redacted("personal"))
        self.assertTrue(R.is_redacted("corporate"))
        self.assertTrue(R.is_redacted("social"))


class RedactSamplesTest(unittest.TestCase):
    def _samples(self):
        return [
            {"ts": "2026-01-01T00:00:00+00:00", "tool": "claude", "session_id": "s1",
             "project": "billing-svc", "text": "fix /Users/me/secret with key sk-abc123", "turn_idx": 0},
            {"ts": "2026-02-01T00:00:00+00:00", "tool": "codex", "session_id": "s2",
             "project": "api-gw", "text": "another raw question", "turn_idx": 1},
            {"ts": "2026-03-01T00:00:00+00:00", "tool": "claude", "session_id": "s3",
             "project": "billing-svc", "text": "same project again", "turn_idx": 0},
        ]

    def test_personal_unchanged(self):
        s = self._samples()
        out = R.redact_samples(s, "personal")
        self.assertEqual(out, s)

    def test_corporate_drops_text_and_anonymizes_project(self):
        out = R.redact_samples(self._samples(), "corporate")
        # 원문 텍스트 0
        self.assertTrue(all(x["text"] == "" for x in out))
        # 실제 프로젝트명 0, 익명 라벨로
        names = {x["project"] for x in out}
        self.assertNotIn("billing-svc", names)
        self.assertNotIn("api-gw", names)
        self.assertTrue(all(p.startswith("project-") for p in names))
        # 같은 원본 프로젝트 → 같은 라벨 (결정적, 일관성)
        self.assertEqual(out[0]["project"], out[2]["project"])
        self.assertNotEqual(out[0]["project"], out[1]["project"])
        # 비파괴: ts/tool/길이용 메타는 유지
        self.assertEqual(out[0]["tool"], "claude")

    def test_social_also_drops(self):
        out = R.redact_samples(self._samples(), "social")
        self.assertTrue(all(x["text"] == "" for x in out))

    def test_no_mutation_of_input(self):
        s = self._samples()
        R.redact_samples(s, "corporate")
        self.assertEqual(s[0]["text"], "fix /Users/me/secret with key sk-abc123")  # 원본 보존


class RedactionSummaryTest(unittest.TestCase):
    """정제 영수증 — 실제 정제 동작을 정직하게 카운트(탐지 우기기 금지)."""

    def _samples(self):
        return [
            {"project": "billing-svc", "text": "raw one"},
            {"project": "api-gw", "text": "raw two"},
            {"project": "billing-svc", "text": "raw three"},
            {"project": None, "text": "   "},   # 공백만 → 원문 없음으로 카운트 제외
        ]

    def test_personal_no_redaction(self):
        s = R.redaction_summary(self._samples(), "personal")
        self.assertFalse(s["redacted"])
        self.assertEqual(s["raw_texts_removed"], 0)
        self.assertEqual(s["projects_anonymized"], 0)
        self.assertEqual(s["template"], "personal")

    def test_corporate_counts(self):
        s = R.redaction_summary(self._samples(), "corporate")
        self.assertTrue(s["redacted"])
        self.assertEqual(s["raw_texts_removed"], 3)     # 공백만인 1건 제외
        self.assertEqual(s["projects_anonymized"], 2)   # billing-svc, api-gw

    def test_social_counts(self):
        s = R.redaction_summary(self._samples(), "social")
        self.assertTrue(s["redacted"])
        self.assertEqual(s["raw_texts_removed"], 3)
        self.assertEqual(s["projects_anonymized"], 2)

    def test_unknown_falls_back_personal(self):
        s = R.redaction_summary(self._samples(), "bogus")
        self.assertFalse(s["redacted"])
        self.assertEqual(s["raw_texts_removed"], 0)


class StripQuotesTest(unittest.TestCase):
    def test_strips_double_and_curly(self):
        self.assertNotIn("how do I", R.strip_quotes('he asked "how do I run docker?" yesterday'))
        self.assertNotIn("why", R.strip_quotes('“why is this slow” was the question'))

    def test_preserves_contractions(self):
        # 작은따옴표 축약형은 건드리지 않는다
        self.assertEqual(R.strip_quotes("don't change this"), "don't change this")

    def test_strips_single_quoted_question(self):
        # 인용처럼 쓰인 홑따옴표(앞뒤가 공백/문장부호)는 제거 — 원문 질문 누출 차단
        out = R.strip_quotes("대표 질문: 'how do I deploy the gateway?' 입니다")
        self.assertNotIn("how do I deploy the gateway", out)

    def test_preserves_possessive_and_contraction_mid_text(self):
        # 소유격·축약형(따옴표가 글자에 붙음)은 보존
        s = "don't touch the worker's queue"
        self.assertEqual(R.strip_quotes(s), s)

    def test_non_string_passthrough(self):
        self.assertEqual(R.strip_quotes(None), None)


class SanitizeInsightsTest(unittest.TestCase):
    def test_strips_quotes_in_evidence_and_narrative(self):
        ins = {
            "summary": 'mostly asked "how do I deploy?" early on',
            "dimensions": {
                "depth": {"narrative": 'shifted from "how" to "why"',
                          "evidence": ['e.g. "how do I run docker?" in April', 'length doubled']},
            },
            "chapters": [{"title": "t", "period": "p", "narrative": 'asked "fix this" a lot'}],
        }
        out = R.sanitize_insights(ins)
        self.assertNotIn("how do I deploy", out["summary"])
        self.assertNotIn("how do I run docker", out["dimensions"]["depth"]["evidence"][0])
        self.assertNotIn("fix this", out["chapters"][0]["narrative"])
        # 인용 없는 evidence는 유지
        self.assertIn("length doubled", out["dimensions"]["depth"]["evidence"])
        # 입력 비파괴
        self.assertIn("how do I deploy", ins["summary"])

    def test_strips_quotes_in_skill_suggestions(self):
        ins = {
            "skill_suggestions": [
                {"name": "deploy-runbook",
                 "why": 'deploy를 반복하며 "deploy the billing service" 같은 맥락을 재설명',
                 "evidence": ['예: "how do I deploy the gateway?" 4회', "count=4"],
                 "est_savings": '회당 "긴 맥락" 재설명 제거',
                 "seed": 'skill: 입력은 "서비스명"'},
            ],
        }
        out = R.sanitize_insights(ins)
        s = out["skill_suggestions"][0]
        self.assertNotIn("deploy the billing service", s["why"])
        self.assertNotIn("how do I deploy the gateway", s["evidence"][0])
        self.assertIn("count=4", s["evidence"])            # 인용 없는 항목 유지
        self.assertNotIn("긴 맥락", s["est_savings"])
        self.assertNotIn("서비스명", s["seed"])
        # 입력 비파괴
        self.assertIn("deploy the billing service", ins["skill_suggestions"][0]["why"])

    def test_strips_single_quoted_raw_prompt_in_seed(self):
        # seed는 예시 질문을 담는 고위험 필드 — 홑따옴표 원문도 corporate에서 제거돼야.
        ins = {"skill_suggestions": [{
            "name": "x", "why": "y", "evidence": ["count=4"],
            "seed": "대표 질문: 'how do I deploy the billing service?'"}]}
        out = R.sanitize_insights(ins)
        self.assertNotIn("how do I deploy the billing service",
                         out["skill_suggestions"][0]["seed"])
