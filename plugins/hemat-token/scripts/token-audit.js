#!/usr/bin/env node
// Token audit for Claude Code transcripts (*.jsonl).
// Usage: node token-audit.js [transcript.jsonl ...]   (default: newest transcript under ~/.claude/projects)
// Prices are relative to 1 uncached input token (Anthropic multipliers): cache read 0.1x,
// cache write 1.25x (5 min) / 2x (1 h), output 5x. "Saving" = 1 - actual / same tokens with no caching.
const fs = require('fs');
const path = require('path');
const os = require('os');

const W = { input: 1, read: 0.1, write5m: 1.25, write1h: 2, output: 5 };

function newestTranscript() {
  const root = path.join(process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude'), 'projects');
  let best = null;
  for (const dir of fs.existsSync(root) ? fs.readdirSync(root) : []) {
    const d = path.join(root, dir);
    if (!fs.statSync(d).isDirectory()) continue;
    for (const f of fs.readdirSync(d)) {
      if (!f.endsWith('.jsonl')) continue;
      const m = fs.statSync(path.join(d, f)).mtimeMs;
      if (!best || m > best.m) best = { p: path.join(d, f), m };
    }
  }
  return best && best.p;
}

function audit(files) {
  const byId = new Map(); // streamed messages repeat the same id; the last copy has the final usage
  let toolResultChars = 0;
  const bigResults = [];
  for (const file of files) {
    for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
      if (!line.trim()) continue;
      let e;
      try { e = JSON.parse(line); } catch { continue; }
      const m = e.message;
      if (e.type === 'assistant' && m && m.usage) byId.set(m.id || e.uuid, m.usage);
      if (e.type === 'user' && m && Array.isArray(m.content)) {
        for (const c of m.content) {
          if (c.type !== 'tool_result') continue;
          const n = JSON.stringify(c.content || '').length;
          toolResultChars += n;
          bigResults.push(n);
        }
      }
    }
  }
  const t = { calls: byId.size, input: 0, read: 0, write5m: 0, write1h: 0, output: 0 };
  for (const u of byId.values()) {
    t.input += u.input_tokens || 0;
    t.read += u.cache_read_input_tokens || 0;
    const cw = u.cache_creation_input_tokens || 0;
    const h1 = (u.cache_creation && u.cache_creation.ephemeral_1h_input_tokens) || 0;
    t.write1h += h1;
    t.write5m += cw - h1;
    t.output += u.output_tokens || 0;
  }
  const allIn = t.input + t.read + t.write5m + t.write1h;
  const actual = t.input * W.input + t.read * W.read + t.write5m * W.write5m + t.write1h * W.write1h + t.output * W.output;
  const noCache = allIn * W.input + t.output * W.output;
  bigResults.sort((a, b) => b - a);
  return {
    ...t,
    allInput: allIn,
    cacheHitRate: allIn ? t.read / allIn : 0,
    weightedActual: actual,
    weightedNoCache: noCache,
    saving: noCache ? 1 - actual / noCache : 0,
    toolResultTokensApprox: Math.round(toolResultChars / 4),
    biggestToolResultsApprox: bigResults.slice(0, 3).map((n) => Math.round(n / 4)),
  };
}

function report(r) {
  const pct = (x) => (x * 100).toFixed(1) + '%';
  const k = (x) => (x / 1000).toFixed(1) + 'k';
  const grade = r.saving >= 0.85 ? 'A' : r.saving >= 0.7 ? 'B' : r.saving >= 0.5 ? 'C' : 'D';
  const tips = [];
  if (r.cacheHitRate < 0.8) tips.push('Cache hit < 80%: avoid editing CLAUDE.md/rules mid-session, avoid long idle gaps (cache expires).');
  if (r.output * 5 > r.weightedActual * 0.4) tips.push('Output > 40% of cost: shorter answers, no pasted files, let Edit carry diffs.');
  if (r.biggestToolResultsApprox[0] > 8000) tips.push(`A tool result was ~${k(r.biggestToolResultsApprox[0])} tokens: grep + offset/limit, pipe to tail/head.`);
  return [
    `API calls           : ${r.calls}`,
    `Input total         : ${k(r.allInput)}  (uncached ${k(r.input)}, cache read ${k(r.read)}, cache write ${k(r.write5m + r.write1h)})`,
    `Output              : ${k(r.output)}`,
    `Cache hit rate      : ${pct(r.cacheHitRate)}`,
    `Weighted cost       : ${k(r.weightedActual)} vs ${k(r.weightedNoCache)} without caching`,
    `Saving              : ${pct(r.saving)}  grade ${grade}  (target A = >=85%)`,
    `Tool results (~tok) : ${k(r.toolResultTokensApprox)}  biggest: ${r.biggestToolResultsApprox.map(k).join(', ') || '-'}`,
    ...(tips.length ? ['Fix next:', ...tips.map((s) => '  - ' + s)] : ['No leaks found.']),
  ].join('\n');
}

if (require.main === module) {
  const files = process.argv.slice(2);
  if (!files.length) {
    const f = newestTranscript();
    if (!f) { console.error('No transcript found. Pass a .jsonl path.'); process.exit(1); }
    files.push(f);
  }
  console.log(`Transcript: ${files.join(', ')}\n` + report(audit(files)));
}

module.exports = { audit, report, W };
