#!/usr/bin/env python3
"""Generate the 100% SYNTHETIC dataset behind the Promptprint demo report.

This is FAKE data — no real prompts, no personal logs. It exists only so the
public demo (the project homepage) can be reproduced and inspected. It models a
believable growth arc over five months: short "how do I…" lookups early on,
maturing into long multi-step specs with code blocks and explicit trade-offs.

Reproduce the live demo:

    python3 examples/demo/generate_demo_data.py        # writes claude.jsonl + codex.jsonl here
    PYTHONPATH=scripts python3 -m wami.cli aggregate \\
        --claude examples/demo/claude.jsonl --codex examples/demo/codex.jsonl \\
        --out /tmp/demo-aggregates.json
    PYTHONPATH=scripts python3 -m wami.cli render \\
        --insights examples/demo/insights.demo.json --aggregates /tmp/demo-aggregates.json \\
        --out /tmp/index.html
"""
import json
import os

OUT = os.path.dirname(os.path.abspath(__file__))

MONTHS = ["2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
PER_MONTH = [80, 110, 150, 175, 185]  # ramps up, peak in Jun
PROJECTS = ["api-gateway", "billing-service", "web-client", "data-pipeline"]
HOURS = [9, 10, 11, 14, 15, 16, 17, 21, 22, 23]

EARLY = [
    "how do I install {t}?",
    "what does {t} actually do?",
    "how to fix a {t} error on startup?",
    "how do I run {t} locally?",
    "quick {t} question: how to undo the last change?",
    "how do I configure {t} for a new project?",
]
EARLY_T = ["docker", "git", "pip", "npm", "venv", "pytest", "bash", "make"]

MID = [
    "what's the difference between {a} and {b}?",
    "why is {a} slower than {b} on a cold start?",
    "{a} vs {b} for the {p} service — what are the trade-offs?",
    "how do I cache the {a} build layer so CI is faster?",
    "is {a} the right choice for {p}, or am I overcomplicating it?",
]
MID_A = ["kubernetes", "redis", "postgres", "docker", "github-actions", "nginx"]
MID_B = ["a plain vm", "memcached", "sqlite", "a shell script", "jenkins", "haproxy"]

LATE = [
    ("Current {p} setup:\n```\nservice -> redis -> postgres\np99 latency ~ 800ms\n```\n"
     "Goals:\n1. cut p99 latency under 200ms\n2. keep the cache warm after deploys\n"
     "3. avoid a rewrite of the service\nWalk me through the trade-offs of each option "
     "and tell me which approach you would choose — your call. Then verify the plan against the goals."),
    ("Critique this {p} architecture and surface the failure modes:\n```\n"
     "async workers -> queue -> {a}\n```\nWhy not just scale the workers horizontally? "
     "What's the rationale for adding {b}, and what are the risks to latency and throughput?"),
    ("Deciding between {a} and {b} for the {p} data layer:\n1. list the trade-offs\n"
     "2. pick one for a read-heavy workload and justify it\n3. double-check it against the latency budget\n"
     "You decide, but show the reasoning."),
    ("Throughput problem in {p}:\n```\n2k req/s, CPU bound on serialization\n```\nSteps:\n"
     "1. profile where the time goes\n2. propose two architectures with trade-offs\n"
     "3. verify each against a 99.9% availability target\nAre you sure batching won't hurt tail latency?"),
]
LATE_A = ["postgres", "kafka", "redis", "the event log", "sharding", "a read replica"]
LATE_B = ["a message queue", "a second cache tier", "an index", "backpressure"]


def phase(mi):
    return "early" if mi <= 1 else ("mid" if mi == 2 else "late")


def make_text(mi, i):
    p = PROJECTS[i % len(PROJECTS)]
    ph = phase(mi)
    if ph == "early":
        return EARLY[i % len(EARLY)].format(t=EARLY_T[i % len(EARLY_T)])
    if ph == "mid":
        return MID[i % len(MID)].format(a=MID_A[i % len(MID_A)], b=MID_B[i % len(MID_B)], p=p)
    return LATE[i % len(LATE)].format(a=LATE_A[i % len(LATE_A)], b=LATE_B[i % len(LATE_B)], p=p)


def main():
    claude_lines = []
    codex_lines = [json.dumps({"type": "session_meta",
                               "payload": {"id": "demo-codex", "cwd": "/home/dev/data-pipeline"}})]
    gidx = 0
    for mi, month in enumerate(MONTHS):
        for q in range(PER_MONTH[mi]):
            gidx += 1
            day = (q % 27) + 1
            hour = HOURS[q % len(HOURS)]
            minute = (q * 7) % 60
            ts = f"{month}-{day:02d}T{hour:02d}:{minute:02d}:00+00:00"
            text = make_text(mi, gidx)
            proj = PROJECTS[gidx % len(PROJECTS)]
            if gidx % 10 < 7:
                claude_lines.append(json.dumps({
                    "type": "user", "sessionId": f"demo-claude-{month}-{q // 12}",
                    "timestamp": ts, "cwd": f"/home/dev/{proj}",
                    "message": {"role": "user", "content": text},
                }, ensure_ascii=False))
            else:
                codex_lines.append(json.dumps({
                    "timestamp": ts, "type": "event",
                    "payload": {"type": "message", "role": "user",
                                "content": [{"type": "input_text", "text": text}]},
                }, ensure_ascii=False))
    with open(os.path.join(OUT, "claude.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(claude_lines) + "\n")
    with open(os.path.join(OUT, "codex.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(codex_lines) + "\n")
    print(f"wrote {len(claude_lines)} claude + {len(codex_lines) - 1} codex synthetic questions to {OUT}")


if __name__ == "__main__":
    main()
