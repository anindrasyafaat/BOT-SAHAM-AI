---
name: hemat-token
description: Token-efficient but full-quality working method. Use for any long or multi-step task (big codebases, refactors, research, HTML/UI builds) where context and cost add up, or when the user asks to save tokens.
---

# Hemat Token — framework

Tokens cost money in three places. Attack them in order of size:

| Where | Share of cost (typical) | Lever |
|---|---|---|
| Re-sent context (every turn re-sends all history) | 60–90% | prompt cache + keep context small |
| Output | 10–30% (5x input price) | answer-first, diffs not files |
| Tool results | lands in context forever | read narrow, trim at source |

## Plan (before the first tool call)
1. Restate the goal to yourself in one line and list deliverables. This is the checklist for the quality gate.
2. Pick the cheapest path to evidence: Grep/Glob → narrow Read → run. Never browse files "to get a feel".
3. Batch independent calls in one message.

## Execute
- Read with offset/limit around grep hits. Re-read only what changed.
- Trim command output: `| tail -n 40`, `-q`, `grep -m 5`. On failure, read the error lines, not the whole log.
- Wide searches across many files → one subagent, ask it for conclusions only.
- Write/Edit directly; do not paste the file into chat as well.
- For HTML/UI: one file, CSS variables for theme, no framework unless asked, check it renders once (screenshot) instead of re-reading the markup.

## Quality gate (mandatory, cheap)
Before "done":
1. Every deliverable from step 1 is done or reported as not done.
2. Ran the proof (tests/build/screenshot) and read the result.
3. Checked callers/configs/tests the change touches.
4. One line: what was skipped or unverified.

Brevity never overrides the gate. A wrong cheap answer costs more tokens to fix than a right one.

## Measure
Run `/hemat-token:audit-token` (or `node ${CLAUDE_PLUGIN_ROOT}/scripts/token-audit.js`) to see cache hit rate, weighted saving and the biggest tool results.
