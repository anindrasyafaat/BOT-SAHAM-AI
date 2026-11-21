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

// Text: ~4 chars per token. Images are sent as pixels, not base64 text.
// shortcut: flat IMAGE_TOKENS per image, use (w*h)/750 if image sizes are ever logged.
const IMAGE_TOKENS = 1600;
function resultTokens(content) {
  if (!Array.isArray(content)) return Math.round(String(content || '').length / 4);
  return content.reduce((n, b) => n + (b.type === 'image' ? IMAGE_TOKENS : Math.round(String(b.text || '').length / 4)), 0);
}

function audit(files) {
  const byId = new Map(); // streamed messages repeat the same id; the last copy has the final usage
  const toolLabel = new Map(); // tool_use id -> "Read: path"
  const results = [];
  for (const file of files) {
    for (const line of fs.readFileSync(file, 'utf8').split('\n')) {
      if (!line.trim()) continue;
      let e;
      try { e = JSON.parse(line); } catch { continue; }
      const m = e.message;
      if (!m || !(e.type === 'assistant' || e.type === 'user')) continue;
      if (e.type === 'assistant' && m.usage) byId.set(m.id || e.uuid, m.usage);
      for (const c of Array.isArray(m.content) ? m.content : []) {
        if (c.type === 'tool_use') {
          const i = c.input || {};
          const file = i.file_path && String(i.file_path).split(/[\\/]/).slice(-2).join('/'); // tail of the path is the useful part
          const arg = file || i.command || i.pattern || i.query || i.url || i.description || i.skill || '';
          toolLabel.set(c.id, (c.name + (arg ? ': ' + String(arg) : '')).replace(/\s+/g, ' ').slice(0, 120));
        }
        if (c.type === 'tool_result') results.push({ id: c.tool_use_id, tokens: resultTokens(c.content) });
      }
    }
  }
  const t = { calls: byId.size, input: 0, read: 0, write5m: 0, write1h: 0, output: 0 };
  const perCall = [];
  for (const u of byId.values()) {
    t.input += u.input_tokens || 0;
    t.read += u.cache_read_input_tokens || 0;
    const cw = u.cache_creation_input_tokens || 0;
    const h1 = (u.cache_creation && u.cache_creation.ephemeral_1h_input_tokens) || 0;
    t.write1h += h1;
    t.write5m += cw - h1;
    t.output += u.output_tokens || 0;
    perCall.push({ uncached: u.input_tokens || 0, write: cw, read: u.cache_read_input_tokens || 0, output: u.output_tokens || 0 });
  }
  const allIn = t.input + t.read + t.write5m + t.write1h;
  const actual = t.input * W.input + t.read * W.read + t.write5m * W.write5m + t.write1h * W.write1h + t.output * W.output;
  const noCache = allIn * W.input + t.output * W.output;
  results.sort((a, b) => b.tokens - a.tokens);
  const toolResultTokens = results.reduce((n, r) => n + r.tokens, 0);
  return {
    ...t,
    allInput: allIn,
    cacheHitRate: allIn ? t.read / allIn : 0,
    weightedActual: actual,
    weightedNoCache: noCache,
    saving: noCache ? 1 - actual / noCache : 0,
    toolResultTokensApprox: toolResultTokens,
    biggestToolResultsApprox: results.slice(0, 3).map((r) => r.tokens),
    topToolResults: results.slice(0, 10).map((r) => ({ label: toolLabel.get(r.id) || 'tool', tokens: r.tokens })),
    perCall,
  };
}

const k = (x) => (x / 1000).toFixed(1) + 'k';
const grade = (r) => (r.saving >= 0.85 ? 'A' : r.saving >= 0.7 ? 'B' : r.saving >= 0.5 ? 'C' : 'D');

function tips(r) {
  const out = [];
  if (r.cacheHitRate < 0.8) out.push('Cache hit < 80%: jangan ubah CLAUDE.md/aturan di tengah sesi, hindari jeda lama (cache kedaluwarsa).');
  if (r.output * W.output > r.weightedActual * 0.4) out.push('Output > 40% biaya: jawaban lebih ringkas, jangan tempel file utuh, biarkan Edit yang membawa diff.');
  if (r.biggestToolResultsApprox[0] > 8000) out.push(`Satu hasil tool ~${k(r.biggestToolResultsApprox[0])} token: grep + offset/limit, potong output dengan tail/head.`);
  return out;
}

function report(r) {
  const pct = (x) => (x * 100).toFixed(1) + '%';
  const fix = tips(r);
  return [
    `API calls           : ${r.calls}`,
    `Input total         : ${k(r.allInput)}  (uncached ${k(r.input)}, cache read ${k(r.read)}, cache write ${k(r.write5m + r.write1h)})`,
    `Output              : ${k(r.output)}`,
    `Cache hit rate      : ${pct(r.cacheHitRate)}`,
    `Weighted cost       : ${k(r.weightedActual)} vs ${k(r.weightedNoCache)} without caching`,
    `Saving              : ${pct(r.saving)}  grade ${grade(r)}  (target A = >=85%)`,
    `Tool results (~tok) : ${k(r.toolResultTokensApprox)}  biggest: ${r.biggestToolResultsApprox.map(k).join(', ') || '-'}`,
    ...(fix.length ? ['Fix next:', ...fix.map((s) => '  - ' + s)] : ['No leaks found.']),
  ].join('\n');
}

if (require.main === module) {
  const args = process.argv.slice(2);
  const h = args.indexOf('--html');
  const htmlOut = h >= 0 ? args.splice(h, 2)[1] : null;
  if (h >= 0 && !htmlOut) { console.error('--html needs an output path'); process.exit(1); }
  const files = args;
  if (!files.length) {
    const f = newestTranscript();
    if (!f) { console.error('No transcript found. Pass a .jsonl path.'); process.exit(1); }
    files.push(f);
  }
  const r = audit(files);
  console.log(`Transcript: ${files.join(', ')}\n` + report(r));
  if (htmlOut) {
    fs.writeFileSync(htmlOut, require('./report-html').renderHtml(r, { files, grade: grade(r), tips: tips(r), W }));
    console.log(`HTML report: ${path.resolve(htmlOut)}`);
  }
}

module.exports = { audit, report, tips, grade, W };
