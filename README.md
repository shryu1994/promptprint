# Promptprint

> *see how your questions grew up.*

---

## What it touches / What it never does

| | |
|---|---|
| **Reads (read-only)** | `~/.claude/projects/`, `~/.codex/` |
| **Writes (local only)** | `aggregates.json`, `insights.json`, the report HTML — all in your cwd |
| **Network** | **none** — analysis is pure Python stdlib, runs fully offline |

Verify it yourself in 90 seconds:

```
bash verify.sh
```

One command. It greps the analysis package for every network-capable import and exits 0 if none are found. No trust required — the proof is in the code.

---

Promptprint reads the **questions you asked your AI coding agents** (Claude Code, Codex) and shows how your *questioning expertise* evolved over time — like Spotify Wrapped, but for your prompts.

It's open source, so "we don't send your data" is something you can verify in the code, not just trust.

---

## What it shows

Promptprint reads your real questions and reports six dimensions of growth:

| Dimension | What it captures |
|---|---|
| **Topic evolution** | What you ask *about*, and how that terrain shifts and deepens |
| **Depth** | "how do I…" (procedure) → "why is this better…" (principles, trade-offs) |
| **AI meta-skill** | Dictation → directing & verifying — how you *handle* the AI matures |
| **Craft** | Context, constraints, multi-step prompts — fewer round-trips per intent |
| **Mastery** | Topics you asked about intensely, then *graduated* from |
| **Your phases** | Clusters the data finds — your own seasons of work |

Output: a single self-contained HTML report (scroll narrative + inline charts) plus a few **shareable cards** you can save as images.

---

## Install

In Claude Code (or Codex):

```
/plugin marketplace add shryu1994/promptprint
/plugin install promptprint@promptprint
/promptprint:promptprint
```

That's it — no runtime to install. The skill runs the bundled Python (standard library only) and your host agent does the interpretation.

---

## How it works

Five layers, all on your machine:

```
logs → adapters → deterministic aggregation → host-LLM interpretation → render
~/.claude · ~/.codex            (stats, no LLM)        (your agent)         HTML + cards
└──────────────── 🔒 nothing crosses this line; the only network calls are the ones
                     your agent already makes when you use it ─────────────────────┘
```

- **Deterministic skeleton, LLM narration.** A dependency-free Python step turns tens of thousands of questions into stable statistics (same input → same numbers). The host LLM only interprets the aggregates + a stratified sample — never the full transcript — and writes the story on top. Numbers don't dance between runs.
- **The host agent *is* the analysis engine.** Because you're already running Claude Code or Codex, there's no model to install and no key to configure.

---

## Privacy

- `aggregates.json`, `insights.json`, and the report contain your **actual questions** — they are git-ignored by default. **Do not commit them.**
- Review a card before you share it.
- No telemetry. No accounts. No network calls. Run `bash verify.sh` to machine-check the last point.

---

## Supported tools

- ✅ **Claude Code** — `~/.claude/projects`
- ✅ **Codex** — `~/.codex`
- 🚧 Antigravity — on the roadmap (adapter slot exists)

---

## License

MIT © 2026 shryu

---

*Internal note: the analysis package under `scripts/wami/` is the deterministic engine; everything user-facing is "Promptprint".*
