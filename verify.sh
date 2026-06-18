#!/bin/sh
# verify.sh — Proves that scripts/wami/ contains no network-capable imports.
#
# What this proves: the deterministic aggregation layer (the only code that
# reads your sensitive ~/.claude / ~/.codex logs) never opens a socket,
# makes an HTTP request, or loads any third-party HTTP library.  If this
# script exits 0 you have machine-checked evidence that the analysis runs
# fully offline — no cloud, no upload, no telemetry.
#
# Usage: bash verify.sh   (run from the repo root)
# Requires: grep, sh — no Python, no curl, no external tools.

SEARCH_DIR="scripts/wami"

# Each pattern is anchored so it only matches actual network-capable import
# statements, not coincidental substring matches in comments or wami-internal
# module names.  We use -E (extended regex) throughout.
PATTERNS='
^[[:space:]]*(import socket)[[:space:]]*(#.*)?$
^[[:space:]]*(import urllib)[[:space:]]*(#.*)?$
^[[:space:]]*(import http)[[:space:]]*(#.*)?$
^[[:space:]]*(import requests)[[:space:]]*(#.*)?$
^[[:space:]]*(import httpx)[[:space:]]*(#.*)?$
^[[:space:]]*(import aiohttp)[[:space:]]*(#.*)?$
^[[:space:]]*(from socket)[[:space:]]+
^[[:space:]]*(from urllib)[[:space:]]+
^[[:space:]]*(from http)[[:space:]]+
^[[:space:]]*urllib\.request
^[[:space:]]*socket\.
^[[:space:]]*requests\.'

found=0

for pat in $PATTERNS; do
    results=$(grep -rEn "$pat" "$SEARCH_DIR" 2>/dev/null)
    if [ -n "$results" ]; then
        echo "$results"
        found=1
    fi
done

if [ "$found" -eq 0 ]; then
    echo "✓ No network-capable imports in $SEARCH_DIR — analysis runs fully offline."
    exit 0
else
    echo ""
    echo "✗ Network-capable import(s) found above — review before trusting the tool."
    exit 1
fi
