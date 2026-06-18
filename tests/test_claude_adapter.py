import json
import os
import tempfile
import unittest
import tests.conftest_path  # noqa: F401
from wami.adapters.claude import ClaudeAdapter

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "claude_sample.jsonl")


class ClaudeAdapterTest(unittest.TestCase):
    def setUp(self):
        self.recs = list(ClaudeAdapter().iter_records_from_file(FIX))

    def test_only_real_questions(self):
        texts = [r.text for r in self.recs]
        self.assertEqual(len(texts), 2)
        self.assertIn("how do I cache results in python?", texts)
        self.assertIn("why is lru_cache faster than a manual dict?", texts)

    def test_fields_populated(self):
        r = [r for r in self.recs if r.session_id == "s1"][0]
        self.assertEqual(r.tool, "claude")
        self.assertEqual(r.project, "projA")          # cwd basename
        self.assertEqual(r.ts, "2026-01-05T10:00:00+00:00")
        self.assertEqual(r.turn_idx, 0)               # 세션 내 첫 질문

    def test_turn_index_increments_per_session(self):
        s2 = [r for r in self.recs if r.session_id == "s2"]
        self.assertEqual(s2[0].turn_idx, 0)


class ClaudeTurnIdxIncrementTest(unittest.TestCase):
    def test_turn_idx_increments_across_multiple_questions_same_session(self):
        """같은 세션 내 여러 real question의 turn_idx가 0, 1, 2, ... 순으로 증가한다."""
        lines = [
            json.dumps({"type": "user", "sessionId": "sess-abc",
                        "timestamp": "2026-04-01T08:00:00.000Z",
                        "cwd": "/proj/myapp",
                        "message": {"role": "user", "content": "first real question"}}),
            json.dumps({"type": "user", "sessionId": "sess-abc",
                        "timestamp": "2026-04-01T08:01:00.000Z",
                        "cwd": "/proj/myapp",
                        "message": {"role": "user", "content": "second real question"}}),
            json.dumps({"type": "user", "sessionId": "sess-abc",
                        "timestamp": "2026-04-01T08:02:00.000Z",
                        "cwd": "/proj/myapp",
                        "message": {"role": "user", "content": "third real question"}}),
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(lines) + "\n")
            tmp_path = f.name
        try:
            recs = list(ClaudeAdapter().iter_records_from_file(tmp_path))
            self.assertEqual(len(recs), 3)
            self.assertEqual([r.turn_idx for r in recs], [0, 1, 2])
            self.assertTrue(all(r.session_id == "sess-abc" for r in recs))
        finally:
            os.unlink(tmp_path)
