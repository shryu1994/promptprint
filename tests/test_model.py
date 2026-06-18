import unittest
import tests.conftest_path  # noqa: F401
from wami.model import QuestionRecord, record_from_dict, record_to_dict


class ModelTest(unittest.TestCase):
    def test_roundtrip(self):
        r = QuestionRecord(
            ts="2026-01-02T03:04:05+00:00",
            tool="claude",
            session_id="sess-1",
            project="myproj",
            text="how do I do X?",
            turn_idx=2,
        )
        d = record_to_dict(r)
        self.assertEqual(d["tool"], "claude")
        r2 = record_from_dict(d)
        self.assertEqual(r2, r)

    def test_optional_project(self):
        r = QuestionRecord(
            ts="2026-01-02T03:04:05+00:00",
            tool="codex",
            session_id="s",
            project=None,
            text="why?",
            turn_idx=0,
        )
        self.assertIsNone(record_to_dict(r)["project"])
