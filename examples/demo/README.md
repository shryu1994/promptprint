# Demo (synthetic data)

This folder holds the **100% synthetic** data behind the
[live demo report](https://sh-ryu.com/promptprint/). It is **not real user data** — every question here is
fabricated to model a believable five-month growth arc, so the demo can be shown
publicly without exposing anyone's prompts.

| File | What it is |
|---|---|
| `generate_demo_data.py` | Generates the fake Claude/Codex logs (`claude.jsonl`, `codex.jsonl`) |
| `insights.demo.json` | The interpretation layer for the demo (what a host LLM would write) |

## Reproduce the demo report

```bash
python3 examples/demo/generate_demo_data.py
PYTHONPATH=scripts python3 -m wami.cli aggregate \
  --claude examples/demo/claude.jsonl --codex examples/demo/codex.jsonl \
  --out /tmp/demo-aggregates.json
PYTHONPATH=scripts python3 -m wami.cli render \
  --insights examples/demo/insights.demo.json --aggregates /tmp/demo-aggregates.json \
  --out /tmp/index.html
```

Open `/tmp/index.html` in a browser. The generated `claude.jsonl` / `codex.jsonl`
are git-ignored (analysis inputs), so regenerate them with the script above.
