import os
import unittest
import tests.conftest_path  # noqa: F401
from wami.adapters.jan import JanAdapter, _epoch_to_iso, _user_text

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE = os.path.join(FIXDIR, "jan_sample.jsonl")


class EpochToIsoTest(unittest.TestCase):
    def test_milliseconds(self):
        self.assertTrue(_epoch_to_iso(1751012639307).startswith("2025"))

    def test_seconds(self):
        self.assertTrue(_epoch_to_iso(1751012639).startswith("2025"))

    def test_garbage(self):
        self.assertEqual(_epoch_to_iso("nope"), "")
        self.assertEqual(_epoch_to_iso(None), "")
        self.assertEqual(_epoch_to_iso(True), "")  # bool은 제외


class UserTextTest(unittest.TestCase):
    def test_list_content(self):
        self.assertEqual(_user_text([{"type": "text", "text": {"value": "hi"}}]), "hi")

    def test_string_content(self):
        self.assertEqual(_user_text("plain"), "plain")

    def test_empty(self):
        self.assertIsNone(_user_text([]))


class JanAdapterTest(unittest.TestCase):
    def setUp(self):
        self.recs = list(JanAdapter().iter_records([SAMPLE]))

    def test_only_user_non_noise(self):
        # m1·m3·m4(user) — m2(assistant)·m5(noise) 제외 → 3개
        self.assertEqual(len(self.recs), 3)
        for r in self.recs:
            self.assertEqual(r.tool, "jan")
            self.assertIsNone(r.project)

    def test_extracts_text_both_shapes(self):
        texts = [r.text for r in self.recs]
        self.assertIn("how do I run a local model with Jan?", texts)   # content[].text.value
        self.assertIn("plain string content also works", texts)         # 문자열 content

    def test_timestamps_are_iso(self):
        for r in self.recs:
            self.assertTrue(r.ts.startswith("20"), f"ts not ISO: {r.ts!r}")

    def test_session_id_from_thread_dir(self):
        self.assertEqual(self.recs[0].session_id, "fixtures")

    def test_registered_in_registry(self):
        from wami.adapters import ADAPTERS
        self.assertIn("jan", ADAPTERS)
