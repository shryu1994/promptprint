"""Guard: the public demo report's headline stats must match the tool's own
deterministic aggregator. This stops the showcase artifact from displaying
numbers its own code contradicts — the exact self-inconsistency this project
exists to avoid. Stdlib unittest only (keeps the zero-dependency promise).
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo"


class DemoConsistencyTest(unittest.TestCase):
    def _aggregate(self, tmp):
        env = {**os.environ, "PYTHONPATH": str(ROOT / "scripts")}
        subprocess.run(
            [sys.executable, str(DEMO / "generate_demo_data.py")],
            check=True, env=env, cwd=str(ROOT),
        )
        out = pathlib.Path(tmp) / "agg.json"
        subprocess.run(
            [sys.executable, "-m", "wami.cli", "aggregate",
             "--claude", str(DEMO / "claude.jsonl"),
             "--codex", str(DEMO / "codex.jsonl"),
             "--out", str(out)],
            check=True, env=env, cwd=str(ROOT),
        )
        return json.loads(out.read_text(encoding="utf-8"))

    def test_demo_insights_match_aggregator(self):
        with tempfile.TemporaryDirectory() as tmp:
            agg = self._aggregate(tmp)
        totals = agg["metaskill"]["totals"]
        shape = agg["shape"]
        canonical = {
            "critique": totals["critique"],
            "verify": totals["verify"],
            "delegate": totals["delegate"],
            "counter": totals["counter"],
            "code_block_count": shape["code_block_count"],
            "total": shape["total"],
        }
        text = (DEMO / "insights.demo.json").read_text(encoding="utf-8")
        for key, value in canonical.items():
            self.assertIn(
                str(value), text,
                f"insights.demo.json omits {key}={value} from the aggregator output",
            )
        for stale in ("238", "140", "210 of 700", "stayed low at 70", "~30%"):
            self.assertNotIn(stale, text, f"stale/incorrect demo stat reappeared: {stale}")


if __name__ == "__main__":
    unittest.main()
