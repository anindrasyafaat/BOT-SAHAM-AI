#!/usr/bin/env node
// PreToolUse(Read): deny a whole-file Read of a big text file and point Claude at grep + offset/limit.
// A partial Read (offset or limit set) always passes, so Claude is never stuck.
const fs = require('fs');
const path = require('path');

const MAX_LINES = Number(process.env.HEMAT_TOKEN_MAX_LINES) || 400;
const BINARY = /\.(png|jpe?g|gif|webp|bmp|ico|pdf|ipynb|zip|gz)$/i; // Read renders these specially

function decide(input) {
  const t = (input && input.tool_input) || {};
  const file = t.file_path;
  if (process.env.HEMAT_TOKEN === 'off' || !file || t.offset != null || t.limit != null || BINARY.test(file)) return null;
  let text;
  try {
    if (fs.statSync(file).size > 50 * 1024 * 1024) return null; // shortcut: skip giant files, Read caps them itself
    text = fs.readFileSync(file, 'utf8');
  } catch {
    return null; // missing/unreadable: let Read report the real error
  }
  const lines = text.split('\n').length;
  if (lines <= MAX_LINES) return null;
  return `hemat-token: ${path.basename(file)} has ${lines} lines (limit ${MAX_LINES} for a whole-file Read). ` +
    `Grep for the symbol/section first, then Read with offset/limit around it. ` +
    `If you truly need all of it, Read it in ranges (e.g. offset 1, limit ${MAX_LINES}).`;
}

if (require.main === module) {
  let raw = '';
  process.stdin.on('data', (c) => (raw += c));
  process.stdin.on('end', () => {
    let input;
    try { input = JSON.parse(raw); } catch { process.exit(0); }
    const reason = decide(input);
    if (reason) {
      process.stdout.write(JSON.stringify({
        hookSpecificOutput: { hookEventName: 'PreToolUse', permissionDecision: 'deny', permissionDecisionReason: reason },
      }));
    }
  });
}

module.exports = { decide };
