import json
import os
import re
import unittest
from html import escape
import tests.conftest_path  # noqa: F401
from wami.render import build_report_html

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _e(s):
    # render가 HTML-escape하므로(XSS 방지) 비교도 escape해서 한다.
    return escape(str(s), quote=True)


def _load(name):
    with open(os.path.join(FIXDIR, name), encoding="utf-8") as fh:
        return json.load(fh)


class ScanReceiptRenderTest(unittest.TestCase):
    """신뢰 영수증(meta.scan)이 리포트에 *보이게* 렌더되는지 — 정직성을 표면으로."""

    def _agg_with_scan(self, ratio=0.82):
        agg = _load("aggregates_sample.json")
        agg["meta"]["scan"] = {
            "scanned_blocks": 27486, "kept_questions": 4996,
            "machine_ratio": ratio, "dropped_subagent": 3115,
            "dropped_noise": 18804, "dropped_duplicate": 130,
            "note": "걸러냄",
        }
        return agg

    # 렌더된 요소 마커(CSS의 `.scan-receipt{` 정의와 구분 — 실제 출력에만 나옴)
    MARK = 'class="scan-receipt anim-fadeup'

    def test_receipt_shown_when_machine_filtered(self):
        html = build_report_html(_load("insights_sample.json"), self._agg_with_scan())
        self.assertIn(self.MARK, html)
        self.assertIn("82%", html)
        self.assertIn("27,486", html)   # scanned blocks, 천단위 포맷

    def test_receipt_absent_when_no_scan(self):
        agg = _load("aggregates_sample.json")
        agg["meta"].pop("scan", None)
        html = build_report_html(_load("insights_sample.json"), agg)
        self.assertNotIn(self.MARK, html)

    def test_receipt_absent_when_zero_ratio(self):
        html = build_report_html(_load("insights_sample.json"), self._agg_with_scan(ratio=0.0))
        self.assertNotIn(self.MARK, html)


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.insights = _load("insights_sample.json")
        cls.aggregates = _load("aggregates_sample.json")
        cls.html = build_report_html(cls.insights, cls.aggregates)

    def test_is_full_html_document(self):
        self.assertTrue(self.html.lstrip().startswith("<!DOCTYPE html>"))
        self.assertIn("</html>", self.html)

    def test_self_contained_no_network(self):
        """외부 리소스(폰트·스크립트·이미지) 참조가 없어야 한다 — 네트워크 0."""
        for needle in (
            "http://",
            "https://",
            "fonts.googleapis",
            "@import",
        ):
            self.assertNotIn(needle, self.html, f"외부 리소스 참조 발견: {needle!r}")
        # src= 는 data: 로 시작하는 것만 허용 (base64 font)
        for m in re.finditer(r'src\s*=\s*["\']', self.html):
            after = self.html[m.end(): m.end() + 10]
            self.assertTrue(
                after.startswith("data:"),
                f"non-data src= found near: {self.html[m.start():m.start()+60]!r}",
            )

    def test_has_headline_and_summary(self):
        self.assertIn(_e(self.insights["headline"]), self.html)
        self.assertIn(_e(self.insights["summary"][:20]), self.html)

    def test_has_all_six_dimension_narratives(self):
        for key, dim in self.insights["dimensions"].items():
            self.assertIn(_e(dim["narrative"]), self.html, f"{key} narrative 누락")

    def test_has_chart_data(self):
        # by_month 값이 차트에 찍혀야 한다
        for month in self.aggregates["activity"]["by_month"]:
            # YYYY-MM → YYYY.MM (surge chart label format)
            month_label = month.replace("-", ".")
            self.assertIn(month_label, self.html, f"차트에 월 라벨 {month_label!r} 누락")

    def test_has_all_cards(self):
        for c in self.insights["cards"]:
            self.assertIn(_e(c["headline"]), self.html)
            self.assertIn(_e(c["caption"]), self.html)

    def test_session_shape_line_in_chart(self):
        """session_shape가 있으면 chart 섹션에 세션당 질문·원샷률 한 줄이 나와야 한다."""
        agg = json.loads(json.dumps(self.aggregates))
        agg["session_shape"] = {
            "sessions": 12, "questions_per_session": 3.5,
            "one_shot_sessions": 4, "one_shot_rate": 0.333,
            "size_buckets": {"1": 4, "2-3": 5, "4-7": 3}, "by_month": {},
        }
        out = build_report_html(self.insights, agg)
        chart_start = out.find('id="chart"')
        self.assertNotEqual(chart_start, -1)
        chart_region = out[chart_start:out.find("</section>", chart_start)]
        self.assertIn("세션당 평균 질문", chart_region)
        self.assertIn("3.5", chart_region)
        self.assertIn("33%", chart_region)   # 0.333 → 33%

    def test_session_shape_omitted_when_no_sessions(self):
        """session_shape가 없거나 세션 0이면 줄을 그리지 않는다(빈 안전)."""
        agg = json.loads(json.dumps(self.aggregates))
        agg["session_shape"] = {"sessions": 0, "questions_per_session": 0.0,
                                "one_shot_sessions": 0, "one_shot_rate": 0.0,
                                "size_buckets": {}, "by_month": {}}
        out = build_report_html(self.insights, agg)
        self.assertNotIn("세션당 평균 질문", out)

    def test_genre_mix_line_in_chart(self):
        """genre_mix가 있으면 chart 섹션에 장르 라벨+비율이 나와야 한다."""
        agg = json.loads(json.dumps(self.aggregates))
        agg["genre_mix"] = {
            "total": 10,
            "mix": [{"genre": "build", "count": 5, "rate": 0.5},
                    {"genre": "debug", "count": 3, "rate": 0.3},
                    {"genre": "understand", "count": 2, "rate": 0.2}],
            "by_month": {},
        }
        out = build_report_html(self.insights, agg)
        chart_region = out[out.find('id="chart"'):out.find("</section>", out.find('id="chart"'))]
        self.assertIn("질문 장르", chart_region)
        self.assertIn("구현 50%", chart_region)   # build → 구현, 0.5 → 50%
        self.assertIn("디버그 30%", chart_region)

    def test_genre_mix_omitted_when_empty(self):
        agg = json.loads(json.dumps(self.aggregates))
        agg["genre_mix"] = {"total": 0, "mix": [], "by_month": {}}
        out = build_report_html(self.insights, agg)
        self.assertNotIn("질문 장르", out)

    def test_trust_receipt_shown_when_redacted(self):
        """corporate/social(redacted)이면 공유 안전 영수증이 hero에 나와야 한다."""
        agg = json.loads(json.dumps(self.aggregates))
        agg.setdefault("samples", {})["redaction"] = {
            "template": "corporate", "redacted": True,
            "raw_texts_removed": 23, "projects_anonymized": 5,
        }
        out = build_report_html(self.insights, agg, template="corporate")
        self.assertIn("공유 안전", out)
        self.assertIn("원문 질문 제거 23", out)
        self.assertIn("프로젝트명 익명화 5", out)
        self.assertIn("네트워크 0", out)

    def test_trust_receipt_absent_for_personal(self):
        """personal(정제 0)이면 영수증을 그리지 않는다."""
        agg = json.loads(json.dumps(self.aggregates))
        agg.setdefault("samples", {})["redaction"] = {
            "template": "personal", "redacted": False,
            "raw_texts_removed": 0, "projects_anonymized": 0,
        }
        out = build_report_html(self.insights, agg, template="personal")
        self.assertNotIn("공유 안전", out)

    def test_has_next_bearings(self):
        # 다음 항로 label appears in the HTML (Korean default)
        self.assertIn("다음 항로", self.html)
        for b in self.insights["next_bearings"]:
            self.assertIn(_e(b["title"]), self.html)
            self.assertIn(_e(b["how"]), self.html)

    def test_has_product_name_and_save_button(self):
        self.assertIn("Promptprint", self.html)
        self.assertIn("saveCard", self.html)  # 공유 메커니즘

    def test_escapes_html_injection(self):
        evil = dict(self.insights)
        evil_dims = {k: dict(v) for k, v in self.insights["dimensions"].items()}
        evil_dims["depth"] = {"narrative": "<script>alert(1)</script>", "evidence": ["x"]}
        evil["dimensions"] = evil_dims
        out = build_report_html(evil, self.aggregates)
        self.assertNotIn("<script>alert(1)</script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_deterministic(self):
        again = build_report_html(self.insights, self.aggregates)
        self.assertEqual(self.html, again)

    def test_handles_empty_gracefully(self):
        # 빈 입력에도 크래시하지 않아야 한다
        out = build_report_html({}, {})
        self.assertIn("<!DOCTYPE html>", out)

    # ── NEW: i18n ─────────────────────────────────────────────────────────────

    def test_default_lang_is_korean(self):
        """lang 없으면 한국어 크롬이 나와야 한다."""
        # Korean section labels must be present
        self.assertIn("항로도", self.html)
        self.assertIn("방위", self.html)
        self.assertIn("다음 항로", self.html)
        self.assertIn("기념엽서", self.html)
        self.assertIn("항해일지", self.html)

    def test_english_lang_gives_english_labels(self):
        """lang='en'이면 영어 크롬이 출력돼야 한다."""
        en_insights = dict(self.insights, lang="en")
        out = build_report_html(en_insights, self.aggregates)
        # English section labels
        self.assertIn("Next Bearings", out)
        self.assertIn("Six Bearings", out)
        self.assertIn("Log Entries", out)
        self.assertIn("Save as image", out)
        # Korean section labels must NOT appear
        self.assertNotIn("다음 항로", out)
        self.assertNotIn("항해일지", out)

    def test_unknown_lang_falls_back_to_korean(self):
        """알 수 없는 lang이면 한국어로 폴백."""
        unk_insights = dict(self.insights, lang="zz")
        out = build_report_html(unk_insights, self.aggregates)
        self.assertIn("다음 항로", out)

    # ── NEW: confidence badge ─────────────────────────────────────────────────

    def test_confidence_badge_shown_for_snapshot_tier(self):
        """confidence_tier='snapshot'이면 배지와 노트가 나와야 한다."""
        agg = dict(self.aggregates)
        agg["meta"] = dict(agg["meta"],
                           confidence_tier="snapshot",
                           confidence_note="질문 수가 50개 미만입니다.")
        out = build_report_html(self.insights, agg)
        # The badge div must be rendered (not just the CSS class in the stylesheet)
        self.assertIn('<div class="confidence-badge"', out)
        self.assertIn(_e("질문 수가 50개 미만입니다."), out)

    def test_confidence_badge_absent_for_full_tier(self):
        """confidence_tier='full'이면 배지 div가 없어야 한다."""
        agg = dict(self.aggregates)
        agg["meta"] = dict(agg["meta"], confidence_tier="full",
                           confidence_note="전체 데이터")
        out = build_report_html(self.insights, agg)
        self.assertNotIn('<div class="confidence-badge"', out)

    def test_confidence_badge_absent_when_no_tier(self):
        """confidence_tier 키 없으면 배지 div가 없어야 한다."""
        agg = dict(self.aggregates)
        meta = {k: v for k, v in agg["meta"].items() if k != "confidence_tier"}
        agg = dict(agg, meta=meta)
        out = build_report_html(self.insights, agg)
        self.assertNotIn('<div class="confidence-badge"', out)

    # ── NEW: cards privacy (no raw evidence in cards section) ─────────────────

    def test_cards_contain_no_evidence_text(self):
        """카드 영역에 dimensions evidence의 원문이 노출되면 안 된다."""
        # Collect all evidence strings from all dimensions
        evidence_strings = []
        for dim in self.insights.get("dimensions", {}).values():
            evidence_strings.extend(dim.get("evidence", []))

        if not evidence_strings:
            self.skipTest("evidence data not present in fixture")

        # Isolate the cards section HTML
        # Cards are rendered between id="cards" section and id="bearings"
        cards_start = self.html.find('id="cards"')
        bearings_start = self.html.find('id="bearings"')
        if cards_start == -1 or bearings_start == -1:
            self.fail("cards or bearings section not found in HTML")
        cards_region = self.html[cards_start:bearings_start]

        for ev in evidence_strings:
            # The evidence text itself (escaped) must not appear inside the cards region
            self.assertNotIn(_e(ev), cards_region,
                             f"Evidence text leaked into cards region: {ev!r}")

    def test_cards_only_have_headline_stat_caption(self):
        """카드에는 headline/stat/caption만 있어야 한다 — why/how/narrative 없어야 함."""
        # Check that bearing 'why'/'how' text doesn't appear in card HTML
        # (that would indicate template confusion)
        cards_start = self.html.find('id="cards"')
        bearings_start = self.html.find('id="bearings"')
        if cards_start == -1 or bearings_start == -1:
            self.fail("section markers not found")
        cards_region = self.html[cards_start:bearings_start]

        for b in self.insights.get("next_bearings", []):
            self.assertNotIn(_e(b.get("why", "")), cards_region)
            self.assertNotIn(_e(b.get("how", "")), cards_region)

    # ── NEW: semantic structure ───────────────────────────────────────────────

    def test_has_semantic_headings(self):
        """각 섹션에 h2 태그가 있어야 한다."""
        self.assertGreater(self.html.count("<h2"), 3)

    def test_has_print_media_query(self):
        """@media print 스타일이 포함되어야 한다."""
        self.assertIn("@media print", self.html)

    def test_footer_text(self):
        """푸터에 made with Promptprint · 100% local 문구가 있어야 한다."""
        self.assertIn("made with Promptprint", self.html)
        self.assertIn("100% local", self.html)


class TemplateRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.insights = _load("insights_sample.json")
        cls.aggregates = _load("aggregates_sample.json")

    def test_personal_has_all_sections(self):
        out = build_report_html(self.insights, self.aggregates, template="personal")
        for sec in ('id="chart"', 'id="chapters"', 'id="dims"', 'id="cards"', 'id="bearings"'):
            self.assertIn(sec, out)

    def test_social_is_cards_only(self):
        out = build_report_html(self.insights, self.aggregates, template="social")
        self.assertIn('id="cards"', out)          # 카드 유지
        self.assertIn("hero-number", out)         # hero 유지
        for sec in ('id="chart"', 'id="chapters"', 'id="dims"', 'id="bearings"', 'id="skills"'):
            self.assertNotIn(sec, out, f"social 템플릿에 {sec} 섹션이 남아있음")

    def test_corporate_has_full_sections(self):
        out = build_report_html(self.insights, self.aggregates, template="corporate")
        for sec in ('id="chart"', 'id="chapters"', 'id="dims"', 'id="cards"', 'id="bearings"'):
            self.assertIn(sec, out)

    def test_corporate_strips_quoted_evidence(self):
        """corporate/social 렌더는 evidence/narrative의 따옴표 인용을 제거해야 한다."""
        ins = json.loads(json.dumps(self.insights))  # deep copy
        ins["dimensions"]["depth"] = {
            "narrative": 'shifted from how to why',
            "evidence": ['for example "how do I deploy the billing service?" in April'],
        }
        out = build_report_html(ins, self.aggregates, template="corporate")
        self.assertNotIn("how do I deploy the billing service", out)
        # personal은 그대로 노출(대조)
        out_p = build_report_html(ins, self.aggregates, template="personal")
        self.assertIn(_e("how do I deploy the billing service?"), out_p)

    def test_corporate_strips_quoted_skill_seed(self):
        """corporate 렌더는 skill_suggestions.seed의 따옴표 인용(대표 질문)도 제거해야 한다."""
        ins = json.loads(json.dumps(self.insights))
        ins["skill_suggestions"] = [{
            "name": "deploy-runbook",
            "why": "deploy 반복",
            "evidence": ["count=4"],
            "seed": 'skill 목적: 배포 자동화. 대표 질문: "how do I deploy the gateway to prod?"',
        }]
        out = build_report_html(ins, self.aggregates, template="corporate")
        self.assertNotIn("how do I deploy the gateway to prod", out)
        # personal은 노출(대조)
        out_p = build_report_html(ins, self.aggregates, template="personal")
        self.assertIn(_e("how do I deploy the gateway to prod?"), out_p)


class SkillsSectionRenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.insights = _load("insights_sample.json")
        cls.aggregates = _load("aggregates_sample.json")
        cls.html = build_report_html(cls.insights, cls.aggregates)

    def test_fixture_has_skill_suggestions(self):
        self.assertTrue(self.insights.get("skill_suggestions"))

    def test_skills_section_rendered(self):
        self.assertIn('id="skills"', self.html)
        for s in self.insights["skill_suggestions"]:
            self.assertIn(_e(s["name"]), self.html)
            self.assertIn(_e(s["why"]), self.html)

    def test_skills_evidence_and_seed_present(self):
        s = self.insights["skill_suggestions"][0]
        for ev in s["evidence"]:
            self.assertIn(_e(ev), self.html)        # 실측 근거 노출
        self.assertIn(_e(s["seed"]), self.html)     # 복사 가능한 seed
        self.assertIn(_e(s["est_savings"]), self.html)
        self.assertIn("copySeed", self.html)        # 복사 메커니즘

    def test_skills_label_korean(self):
        self.assertIn("스킬로 만들 것", self.html)

    def test_skills_omitted_when_no_suggestions(self):
        ins = {k: v for k, v in self.insights.items() if k != "skill_suggestions"}
        out = build_report_html(ins, self.aggregates)
        self.assertNotIn('id="skills"', out)

    def test_skills_omitted_when_empty_list(self):
        ins = dict(self.insights, skill_suggestions=[])
        out = build_report_html(ins, self.aggregates)
        self.assertNotIn('id="skills"', out)

    def test_skills_not_in_social(self):
        out = build_report_html(self.insights, self.aggregates, template="social")
        self.assertNotIn('id="skills"', out)

    def test_skills_escapes_injection(self):
        ins = json.loads(json.dumps(self.insights))
        ins["skill_suggestions"][0]["name"] = "<script>alert(2)</script>"
        out = build_report_html(ins, self.aggregates)
        self.assertNotIn("<script>alert(2)</script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_skills_english_label(self):
        en = dict(self.insights, lang="en")
        out = build_report_html(en, self.aggregates)
        self.assertIn("Skills to Build", out)
