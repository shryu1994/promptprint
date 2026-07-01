import os
import unittest
from collections import Counter
import tests.conftest_path  # noqa: F401
from wami.adapters.base import Adapter
from wami.extract import extract_records, _collapse_programmatic, _drop_oversized, OVERSIZE_LEN
from wami.model import QuestionRecord

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

    def test_stats_out_filled(self):
        stats = Counter()
        recs = extract_records(
            {"claude": [os.path.join(FIXDIR, "claude_sample.jsonl")]},
            stats_out=stats,
        )
        self.assertEqual(stats["kept"], len(recs))
        self.assertIn("scanned", stats)
        self.assertGreaterEqual(stats["scanned"], stats["kept"])


def _rec(text, sid, hh=8):
    return QuestionRecord(ts=f"2026-04-01T{hh:02d}:00:00+00:00", tool="claude",
                          session_id=sid, project="p", text=text, turn_idx=0)


class CollapseProgrammaticTest(unittest.TestCase):
    """긴 동일 텍스트가 여러 세션에 반복되면 프로그램적(eval·RAG·배치)으로 보고 제거.
    짧은 반복(continue·1 등 사람 넛지)과 고유한 긴 질문은 보존."""

    def test_long_high_freq_dropped_short_kept(self):
        long_text = "X" * 300
        recs = [_rec(long_text, f"s{i}") for i in range(6)]          # 긴 동일 ×6 → 기계
        recs += [_rec("continue", f"s{i}", hh=9) for i in range(6)]  # 짧은 반복 → 사람
        recs.append(_rec("Y" * 400, "s9"))                          # 고유한 긴 질문 → 보존
        stats = Counter()
        out = _collapse_programmatic(recs, stats)
        texts = [r.text for r in out]
        self.assertNotIn(long_text, texts)
        self.assertEqual(texts.count("continue"), 6)
        self.assertIn("Y" * 400, texts)
        self.assertEqual(stats["dropped_duplicate"], 6)

    def test_below_threshold_kept(self):
        long_text = "Z" * 300
        recs = [_rec(long_text, f"s{i}") for i in range(4)]  # 4회(<5) → 보존
        stats = Counter()
        out = _collapse_programmatic(recs, stats)
        self.assertEqual(len(out), 4)
        self.assertEqual(stats["dropped_duplicate"], 0)


class DropOversizedTest(unittest.TestCase):
    """초대형 블록(사람이 타이핑 안 하는 길이 — 코드리뷰·시큐리티리뷰가 레포 전체를
    쏟아낸 툴 덤프)은 사람 질문이 아니므로 제거. 82% 필터가 놓친 잔여 기계 트래픽."""

    def test_oversized_dropped_normal_kept(self):
        recs = [_rec("x" * (OVERSIZE_LEN + 1), "big"),   # 툴 덤프 → 제거
                _rec("normal human question about deploy", "ok")]
        stats = Counter()
        out = _drop_oversized(recs, stats)
        self.assertEqual([r.session_id for r in out], ["ok"])
        self.assertEqual(stats["dropped_oversized"], 1)

    def test_at_threshold_kept(self):
        recs = [_rec("x" * OVERSIZE_LEN, "edge")]        # 경계값(==)은 보존
        stats = Counter()
        out = _drop_oversized(recs, stats)
        self.assertEqual(len(out), 1)
        self.assertEqual(stats["dropped_oversized"], 0)
