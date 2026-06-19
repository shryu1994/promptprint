import json
import os
import sys
import tempfile
import unittest
import tests.conftest_path  # noqa: F401
from wami.cli import run_aggregate, main

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures")


class CliValidateInsightsTest(unittest.TestCase):
    def test_validate_good_insights(self):
        good = os.path.join(FIXDIR, "insights_sample.json")
        self.assertEqual(main(["validate-insights", good]), 0)

    def test_validate_nonexistent_file(self):
        self.assertEqual(main(["validate-insights", "/nonexistent/path/nope.json"]), 1)

    def test_validate_bad_insights(self):
        import tempfile, json as _json
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.json")
            with open(bad, "w") as fh:
                _json.dump({"schema_version": "1"}, fh)
            self.assertEqual(main(["validate-insights", bad]), 1)


class CliTest(unittest.TestCase):
    def test_run_aggregate_writes_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "aggregates.json")
            run_aggregate(
                roots_by_tool={
                    "claude": [os.path.join(FIXDIR, "claude_sample.jsonl")],
                    "codex": [os.path.join(FIXDIR, "codex_sample.jsonl")],
                },
                out_path=out,
            )
            with open(out) as fh:
                agg = json.load(fh)
            self.assertEqual(agg["meta"]["total_questions"], 4)
            self.assertEqual(set(agg["meta"]["by_tool"]), {"claude", "codex"})
            for section in ("meta", "activity", "shape", "topics", "metaskill", "mastery", "tool_compare", "samples"):
                self.assertIn(section, agg)


class CliMainTest(unittest.TestCase):
    def test_aggregate_only_claude_flag(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "aggregates.json")
            ret = main([
                "aggregate",
                "--out", out,
                "--claude", os.path.join(FIXDIR, "claude_sample.jsonl"),
            ])
            self.assertEqual(ret, 0)
            with open(out) as fh:
                agg = json.load(fh)
            self.assertIn("claude", agg["meta"]["by_tool"])
            self.assertNotIn("codex", agg["meta"]["by_tool"])

    def test_aggregate_both_flags(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "aggregates.json")
            ret = main([
                "aggregate",
                "--out", out,
                "--claude", os.path.join(FIXDIR, "claude_sample.jsonl"),
                "--codex", os.path.join(FIXDIR, "codex_sample.jsonl"),
            ])
            self.assertEqual(ret, 0)
            with open(out) as fh:
                agg = json.load(fh)
            self.assertEqual(agg["meta"]["total_questions"], 4)

    def test_tools_flag_restricts_subset(self):
        """--tools 가 선택한 도구만 집계한다 — 다른 도구 경로가 주어져도 제외된다."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "aggregates.json")
            ret = main([
                "aggregate", "--out", out,
                "--tools", "claude",
                "--claude", os.path.join(FIXDIR, "claude_sample.jsonl"),
                "--codex", os.path.join(FIXDIR, "codex_sample.jsonl"),
            ])
            self.assertEqual(ret, 0)
            with open(out) as fh:
                agg = json.load(fh)
            self.assertIn("claude", agg["meta"]["by_tool"])
            self.assertNotIn("codex", agg["meta"]["by_tool"])

    def test_tool_roots_custom_path_for_any_tool(self):
        """--tool-roots 로 임의 도구(jan)에 커스텀 경로를 지정해 집계한다."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "aggregates.json")
            ret = main([
                "aggregate", "--out", out,
                "--tools", "jan",
                "--tool-roots", "jan:" + os.path.join(FIXDIR, "jan_sample.jsonl"),
            ])
            self.assertEqual(ret, 0)
            with open(out) as fh:
                agg = json.load(fh)
            self.assertEqual(set(agg["meta"]["by_tool"]), {"jan"})
            self.assertEqual(agg["meta"]["total_questions"], 3)

    def test_aggregate_progress_messages_on_stderr(self):
        """정상 실행 시 진행 상황 메시지가 stderr에 출력되는지 확인."""
        import io
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "aggregates.json")
            buf = io.StringIO()
            orig_stderr = sys.stderr
            sys.stderr = buf
            try:
                ret = main([
                    "aggregate",
                    "--out", out,
                    "--claude", os.path.join(FIXDIR, "claude_sample.jsonl"),
                ])
            finally:
                sys.stderr = orig_stderr
            captured = buf.getvalue()
        self.assertEqual(ret, 0)
        self.assertIn("로그를 스캔하는 중", captured)
        self.assertIn("발견", captured)
        self.assertIn("집계하는 중", captured)
        self.assertIn("집계 완료", captured)


class CliAggregateEmptyTest(unittest.TestCase):
    """존재하지 않는/빈 경로를 지정했을 때 안전하게 처리되는지 검증."""

    def test_empty_dir_returns_zero(self):
        """존재하지 않는 경로 → 크래시 없이 0 반환."""
        with tempfile.TemporaryDirectory() as d:
            nonexistent = os.path.join(d, "no_such_dir")
            out = os.path.join(d, "aggregates.json")
            ret = main([
                "aggregate",
                "--out", out,
                "--claude", nonexistent,
                "--codex", nonexistent,
            ])
            self.assertEqual(ret, 0)

    def test_empty_dir_writes_total_zero(self):
        """로그 없음 → aggregates.json의 total_questions 가 0."""
        with tempfile.TemporaryDirectory() as d:
            nonexistent = os.path.join(d, "no_such_dir")
            out = os.path.join(d, "aggregates.json")
            main([
                "aggregate",
                "--out", out,
                "--claude", nonexistent,
            ])
            with open(out) as fh:
                agg = json.load(fh)
            self.assertEqual(agg["meta"]["total_questions"], 0)

    def test_empty_dir_guidance_on_stderr(self):
        """로그 없음 → 안내 메시지가 stderr에 출력된다."""
        import io
        with tempfile.TemporaryDirectory() as d:
            nonexistent = os.path.join(d, "no_such_dir")
            out = os.path.join(d, "aggregates.json")
            buf = io.StringIO()
            orig_stderr = sys.stderr
            sys.stderr = buf
            try:
                main([
                    "aggregate",
                    "--out", out,
                    "--claude", nonexistent,
                ])
            finally:
                sys.stderr = orig_stderr
            captured = buf.getvalue()
        self.assertIn("로그를 찾지 못했습니다", captured)
        self.assertIn("--claude", captured)
        self.assertIn("--codex", captured)
