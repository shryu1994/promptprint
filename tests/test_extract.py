import os
import unittest
import tests.conftest_path  # noqa: F401
from wami.adapters.base import Adapter
from wami.extract import extract_records

FIXDIR = os.path.join(os.path.dirname(__file__), "fixtures")


class _Fake(Adapter):
    tool = "fake"
    def default_roots(self):
        return []
    def iter_records(self, roots):
        return iter(())


class AdapterContractTest(unittest.TestCase):
    def test_subclass_has_tool_name(self):
        a = _Fake()
        self.assertEqual(a.tool, "fake")
        self.assertEqual(list(a.iter_records([])), [])


class ExtractTest(unittest.TestCase):
    def test_merge_and_sort(self):
        recs = extract_records({
            "claude": [os.path.join(FIXDIR, "claude_sample.jsonl")],
            "codex": [os.path.join(FIXDIR, "codex_sample.jsonl")],
        })
        # 두 도구 합쳐 진짜 질문 4개, ts 오름차순 정렬.
        self.assertEqual(len(recs), 4)
        ts_list = [r.ts for r in recs]
        self.assertEqual(ts_list, sorted(ts_list))
        self.assertEqual({r.tool for r in recs}, {"claude", "codex"})
