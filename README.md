# Promptprint

> *see how your questions grew up.*

[![CI](https://github.com/shryu1994/promptprint/actions/workflows/ci.yml/badge.svg)](https://github.com/shryu1994/promptprint/actions/workflows/ci.yml)

Promptprint reads the **questions you've asked your AI coding agents** — Claude Code and Codex — and shows how your *questioning skill* has grown over time. Think Spotify Wrapped, but for your prompts.

Everything runs on your own machine. It's open source, so "your data never leaves your computer" is something you can verify in the code — not just take on trust.

## What you get

A single self-contained HTML report — a scrollable story with inline charts — plus a few **shareable cards** you can save as images. The report is written in your own language.

It covers six dimensions of growth:

| Dimension | What it captures |
|---|---|
| **Topic evolution** | What you ask *about*, and how that ground shifts and deepens |
| **Depth** | "How do I…" (procedure) → "Why is this better…" (principles and trade-offs) |
| **AI meta-skill** | Dictating → directing and verifying: how you *handle* the AI matures |
| **Craft** | Context, constraints, multi-step prompts — fewer round-trips per intent |
| **Mastery** | Topics you once asked about intensely, then *graduated* from |
| **Your phases** | Clusters the tool finds in your data — your own seasons of work |

## Install

In Claude Code (or Codex):

```
/plugin marketplace add shryu1994/promptprint
/plugin install promptprint@promptprint
/promptprint:promptprint
```

That's it — nothing extra to install or run. The skill executes the bundled Python (standard library only), and your host agent does the interpretation.

## How it works

Five layers, all on your machine:

1. **Logs** — read your questions from `~/.claude` and `~/.codex` (read-only).
2. **Adapters** — normalize each tool's format into one common schema.
3. **Aggregate** — deterministic Python statistics: no LLM, same input → same numbers.
4. **Interpret** — your host agent reads the aggregates plus a small sample (never the full transcript) and writes the story.
5. **Render** — a single self-contained HTML report and a few shareable cards.

Two ideas keep it trustworthy:

- **Deterministic skeleton, LLM narration.** The numbers come from plain Python and don't change between runs; the LLM only adds the interpretation on top.
- **Your agent is the engine.** Because you already run Claude Code or Codex, there's no separate model to install and no API key to configure.

## Privacy

Your questions are personal, so privacy is built into the design — not bolted on:

- **Read-only.** Promptprint reads your logs and never changes them.
- **No network.** The analysis is pure Python standard library and runs fully offline. The only network calls are the ones your agent already makes when you use it normally.
- **Verify it yourself in 90 seconds:**
  ```
  bash verify.sh
  ```
  One command scans the analysis code for any network-capable import and exits `0` only if it finds none. The proof is in the code, not a promise.
- **Local output.** `aggregates.json`, `insights.json`, and the report contain your real questions. They are git-ignored by default — don't commit them, and review a card before you share it.
- No telemetry, no accounts, no sign-up.

## Supported tools

| Tool | Logs | Status |
|---|---|---|
| **Claude Code** | `~/.claude/projects` | ✅ Supported |
| **Codex** | `~/.codex` | ✅ Supported |
| Antigravity | — | 🚧 On the roadmap (adapter slot exists) |

## License

MIT © 2026 shryu
