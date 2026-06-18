import json
import os
import tempfile
import unittest
import tests.conftest_path  # noqa: F401
from wami.adapters.codex import CodexAdapter

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "codex_sample.jsonl")


class CodexAdapterTest(unittest.TestCase):
    def setUp(self):
        self.recs = list(CodexAdapter().iter_records_from_file(FIX))

    def test_only_real_user_questions(self):
        texts = sorted(r.text for r in self.recs)
        self.assertEqual(texts, ["how do I stream tokens?", "why does SSE need flush?"])

    def test_tool_and_ts(self):
        r = self.recs[0]
        self.assertEqual(r.tool, "codex")
        self.assertTrue(r.ts.startswith("2026-01-06T11:00:10"))

    def test_developer_role_excluded(self):
        self.assertFalse(any("system injected" in r.text for r in self.recs))


class CodexSessionMetaTwoPassTest(unittest.TestCase):
    def test_meta_after_user_message_still_used(self):
        """session_meta가 user 메시지 뒤에 나와도 meta의 session_id/project가 적용된다."""
        lines = [
            json.dumps({"timestamp": "2026-03-01T10:00:00.000Z", "type": "response_item",
                        "payload": {"type": "message", "role": "user",
                                    "content": [{"type": "input_text", "text": "first question"}]}}),
            json.dumps({"timestamp": "2026-03-01T10:00:01.000Z", "type": "session_meta",
                        "payload": {"id": "meta-session-99", "cwd": "/home/u/meta-project"}}),
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(lines) + "\n")
            tmp_path = f.name
        try:
            recs = list(CodexAdapter().iter_records_from_file(tmp_path))
            self.assertEqual(len(recs), 1)
            self.assertEqual(recs[0].session_id, "meta-session-99")
            self.assertEqual(recs[0].project, "meta-project")
        finally:
            os.unlink(tmp_path)

    def test_no_session_meta_falls_back_to_filename_stem(self):
        """session_meta가 없으면 session_id는 파일명 stem, project는 None이다."""
        lines = [
            json.dumps({"timestamp": "2026-03-01T11:00:00.000Z", "type": "response_item",
                        "payload": {"type": "message", "role": "user",
                                    "content": [{"type": "input_text", "text": "no meta question"}]}}),
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl",
                                         prefix="no-meta-stem-", delete=False) as f:
            f.write("\n".join(lines) + "\n")
            tmp_path = f.name
        try:
            expected_stem = os.path.splitext(os.path.basename(tmp_path))[0]
            recs = list(CodexAdapter().iter_records_from_file(tmp_path))
            self.assertEqual(len(recs), 1)
            self.assertEqual(recs[0].session_id, expected_stem)
            self.assertIsNone(recs[0].project)
        finally:
            os.unlink(tmp_path)
