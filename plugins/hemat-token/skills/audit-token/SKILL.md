---
name: audit-token
description: Audit token usage of the current (or a given) Claude Code session - cache hit rate, weighted cost saving vs no caching, biggest tool results, and what to fix next. Use when the user asks how many tokens were used, whether the saving works, or for a token audit.
---

# Audit token

1. Run: `node "${CLAUDE_PLUGIN_ROOT}/scripts/token-audit.js"` (newest transcript), or pass `.jsonl` paths the user names.
2. Show the report as-is.
3. Add at most 3 concrete fixes, taken from the report's "Fix next" lines, applied to this session's actual behaviour.

Grades: A >= 85% weighted saving, B >= 70%, C >= 50%, D below. The saving comes mostly from prompt caching; context discipline keeps it there as the session grows.
