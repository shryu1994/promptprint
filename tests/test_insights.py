import json
import os
import unittest
import tests.conftest_path  # noqa: F401
from wami.insights import validate_insights, DIMENSION_KEYS

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _valid():
    return {
        "schema_version": "1",
        "headline": "질문이 절차에서 설계로 옮겨갔다",
        "summary": "초기에는 사용법을 묻다가 점차 트레이드오프를 묻기 시작했다. " * 2,
        "dimensions": {
            k: {"narrative": f"{k} 서사", "evidence": [f"{k} 근거: 수치 12"]}
            for k in DIMENSION_KEYS
        },
        "chapters": [
            {"title": "탐색기", "period": "2026-04 ~ 2026-05", "narrative": "기초를 물었다"}
        ],
        "cards": [
            {"headline": "+213%", "stat": "더 깊은 질문", "caption": "작년 대비"},
            {"headline": "7,562", "stat": "총 질문", "caption": "3개월"},
            {"headline": "docker", "stat": "졸업한 주제", "caption": "더는 묻지 않음"},
        ],
        "next_bearings": [
            {"title": "코드 맥락 함께 주기", "why": "코드블록 동반률 7%로 낮음", "how": "에러·파일을 붙여 한 번에 풀기"},
            {"title": "졸업 주제 정리", "why": "docker는 더는 묻지 않음", "how": "다음 난이도 주제로 이동"},
        ],
    }


class InsightsValidatorTest(unittest.TestCase):
    def test_valid_passes(self):
        self.assertEqual(validate_insights(_valid()), [])

    def test_too_few_bearings(self):
        o = _valid(); o["next_bearings"] = o["next_bearings"][:1]
        self.assertTrue(any("next_bearings" in e for e in validate_insights(o)))

    def test_empty_bearing_field(self):
        o = _valid(); o["next_bearings"][0]["how"] = "   "
        self.assertTrue(any("next_bearings[0].how" in e for e in validate_insights(o)))

    def test_missing_top_level_key(self):
        o = _valid(); del o["headline"]
        errs = validate_insights(o)
        self.assertTrue(any("headline" in e for e in errs))

    def test_wrong_schema_version(self):
        o = _valid(); o["schema_version"] = "2"
        self.assertTrue(any("schema_version" in e for e in validate_insights(o)))

    def test_missing_dimension(self):
        o = _valid(); del o["dimensions"]["depth"]
        self.assertTrue(any("depth" in e for e in validate_insights(o)))

    def test_empty_narrative(self):
        o = _valid(); o["dimensions"]["craft"]["narrative"] = "   "
        self.assertTrue(any("craft" in e and "narrative" in e for e in validate_insights(o)))

    def test_empty_evidence(self):
        o = _valid(); o["dimensions"]["mastery"]["evidence"] = []
        self.assertTrue(any("mastery" in e and "evidence" in e for e in validate_insights(o)))

    def test_too_few_cards(self):
        o = _valid(); o["cards"] = o["cards"][:2]
        self.assertTrue(any("cards" in e for e in validate_insights(o)))

    def test_too_many_cards(self):
        o = _valid(); o["cards"] = o["cards"] * 2  # 6개
        self.assertTrue(any("cards" in e for e in validate_insights(o)))

    def test_no_chapters(self):
        o = _valid(); o["chapters"] = []
        self.assertTrue(any("chapters" in e for e in validate_insights(o)))

    def test_empty_chapter_field(self):
        o = _valid()
        o["chapters"][0]["narrative"] = "   "
        self.assertTrue(any("chapters[0].narrative" in e for e in validate_insights(o)))

    def test_missing_schema_version(self):
        o = _valid(); del o["schema_version"]
        self.assertTrue(any("schema_version" in e for e in validate_insights(o)))


class InsightsFixtureTest(unittest.TestCase):
    def test_golden_insights_is_valid(self):
        with open(os.path.join(FIXDIR, "insights_sample.json"), encoding="utf-8") as fh:
            obj = json.load(fh)
        self.assertEqual(validate_insights(obj), [])

    def test_golden_aggregates_has_8_sections(self):
        with open(os.path.join(FIXDIR, "aggregates_sample.json"), encoding="utf-8") as fh:
            agg = json.load(fh)
        for s in ("meta", "activity", "shape", "topics", "metaskill", "mastery", "tool_compare", "samples"):
            self.assertIn(s, agg)
