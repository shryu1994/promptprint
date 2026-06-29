# Promptprint

> *Your AI coding agent gets the credit. Promptprint shows how good* **you** *got at asking — and what to fix next.*

[![CI](https://github.com/shryu1994/promptprint/actions/workflows/ci.yml/badge.svg)](https://github.com/shryu1994/promptprint/actions/workflows/ci.yml)

Promptprint reads the **questions you've sent your AI coding agents** (Claude Code, Codex), 100% on your own machine, and measures the one thing nothing else does: **how *you* ask — and how that's changing.**

Every other tool measures your *agent* — tokens, cost, lines accepted, streaks. The year-end "AI Wrapped" recaps are a card you open once. This is different: a **recurring check** on your questioning skill that ends with *what to change next*, not a number to feel good about.

It's open source and offline by design, so "your data never leaves your computer" is something you can **verify in the code** (`bash verify.sh`) — not take on trust.

[![Promptprint demo report — a field journal of how your questions to AI coding agents grew over five months](examples/demo/report-preview.png)](https://sh-ryu.com/promptprint/)

**▶ [See the live demo report →](https://sh-ryu.com/promptprint/)** — built from 100% synthetic data, no real prompts.

## What you get

**A recurring check — the one you actually re-run.** `/promptprint check` compares your last 30 days to the 30 before: what moved in *how you ask* (verifying more? directing more? fewer round-trips per task?), what new ground you're on, and — most useful — **the repeated work you keep re-explaining, ready to turn into a skill** instead of pasting it again. Length-robust rates, not flattering raw counts.

**A growth report** — a single self-contained HTML field journal (+ shareable cards), in your own language. It opens with **what to do next** — next bearings, and skills to create from the repeated work in your logs (each with a ready-to-paste `/skill-creator` seed and an *honest, measured* saving estimate: the counts are real, the saving is flagged as an estimate with its assumptions shown) — then the retrospective, across six dimensions of growth:

| Dimension | What it captures |
|---|---|
| **Topic evolution** | What you ask *about*, and how that ground shifts and deepens |
| **Depth** | "How do I…" (procedure) → "Why is this better…" (principles and trade-offs) |
| **AI meta-skill** | Dictating → directing and verifying: how you *handle* the AI matures |
| **Craft** | Context, constraints, multi-step prompts — fewer round-trips per intent |
| **Mastery** | Topics you once asked about intensely, then *graduated* from |
| **Your phases** | Clusters the tool finds in your data — your own seasons of work |

It also surfaces two things you can **share without oversharing**: your **session shape** (round-trips per task, one-shot rate — the numbers you can actually move) and a **question-genre mix** (debug / build / understand / improve) — the texture of *what* you ask, in counts, never raw text.

Two speeds, same local data: the check for a quick nudge between sessions, the full report when you want the whole arc.

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
- **Safe-to-share receipt.** When you build a report for your team or socially (`--template corporate`/`social`), it carries a receipt of what was scrubbed — raw questions removed, project names anonymized, zero network — so "safe to share" is shown, not assumed.
- No telemetry, no accounts, no sign-up.

## Supported tools

| Tool | Logs | Status |
|---|---|---|
| **Claude Code** | `~/.claude/projects` | ✅ Supported |
| **Codex** | `~/.codex` | ✅ Supported |
| **Jan** | `<Jan data>/threads/*/messages.jsonl` | ✅ Supported |
| Cursor | `state.vscdb` (SQLite) | 🚧 Roadmap (local logs are timestamp-light) |
| Antigravity | `~/.gemini/antigravity/…` | 🚧 IDE logs are encrypted — under investigation |

Pick which tools to include with `--tools` (e.g. `--tools claude jan`); point any tool at a custom path with `--tool-roots tool:/path`. Adding a tool is one small adapter (`scripts/wami/adapters/`).

## License

MIT © 2026 shryu
