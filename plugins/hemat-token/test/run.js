#!/usr/bin/env node
// Self-check: node plugins/hemat-token/test/run.js
const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { decide } = require('../hooks/read-guard');
const { audit, report } = require('../scripts/token-audit');

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'hemat-'));
const small = path.join(tmp, 'small.txt');
const big = path.join(tmp, 'big.txt');
fs.writeFileSync(small, 'a\n'.repeat(10));
fs.writeFileSync(big, 'a\n'.repeat(1000));

// read-guard
assert.strictEqual(decide({ tool_input: { file_path: small } }), null, 'small file passes');
assert.match(decide({ tool_input: { file_path: big } }), /1001 lines/, 'big whole-file read denied');
assert.strictEqual(decide({ tool_input: { file_path: big, limit: 50 } }), null, 'partial read passes');
assert.strictEqual(decide({ tool_input: { file_path: big, offset: 0 } }), null, 'offset 0 counts as partial');
assert.strictEqual(decide({ tool_input: { file_path: path.join(tmp, 'x.png') } }), null, 'binary passes');
assert.strictEqual(decide({ tool_input: { file_path: path.join(tmp, 'missing.txt') } }), null, 'missing passes');
const hookOut = execFileSync('node', [path.join(__dirname, '../hooks/read-guard.js')], {
  input: JSON.stringify({ tool_name: 'Read', tool_input: { file_path: big } }),
}).toString();
assert.strictEqual(JSON.parse(hookOut).hookSpecificOutput.permissionDecision, 'deny', 'hook emits deny JSON');

// audit: duplicate streamed id counted once; 1h vs 5m cache writes split
const tr = path.join(tmp, 't.jsonl');
const usage = (id, u) => JSON.stringify({ type: 'assistant', message: { id, usage: u } });
fs.writeFileSync(tr, [
  usage('m1', { input_tokens: 999, output_tokens: 1 }), // stale streamed copy
  usage('m1', { input_tokens: 10, cache_creation_input_tokens: 1000, cache_creation: { ephemeral_1h_input_tokens: 600 }, output_tokens: 100 }),
  usage('m2', { input_tokens: 10, cache_read_input_tokens: 9000, output_tokens: 100 }),
  JSON.stringify({ type: 'user', message: { content: [{ type: 'tool_result', content: 'x'.repeat(400) }] } }),
  JSON.stringify({ type: 'assistant', message: { content: [{ type: 'tool_use', id: 't2', name: 'Read', input: { file_path: '/a/b/c/shot.png' } }] } }),
  JSON.stringify({ type: 'user', message: { content: [{ type: 'tool_result', tool_use_id: 't2', content: [{ type: 'image', source: { data: 'A'.repeat(400000) } }] }] } }),
  'not json',
].join('\n'));
const r = audit([tr]);
assert.strictEqual(r.calls, 2);
assert.strictEqual(r.input, 20);
assert.strictEqual(r.write1h, 600);
assert.strictEqual(r.write5m, 400);
assert.strictEqual(r.read, 9000);
assert.strictEqual(r.output, 200);
// actual = 20 + 900 + 500 + 1200 + 1000 = 3620; noCache = 10020 + 1000 = 11020
assert.strictEqual(r.weightedActual, 3620);
assert.strictEqual(r.weightedNoCache, 11020);
assert.match(report(r), /Saving\s+: 67\.2%/);
assert.deepStrictEqual(r.topToolResults[0], { label: 'Read: c/shot.png', tokens: 1600 }, 'image counted flat, path tail kept');
assert.strictEqual(r.toolResultTokensApprox, 1700);
assert.deepStrictEqual(r.perCall.map((c) => c.read), [0, 9000]);

// html report renders and escapes transcript text
const { renderHtml } = require('../scripts/report-html');
const { tips, grade, W } = require('../scripts/token-audit');
r.topToolResults.push({ label: 'Bash: echo </script><b>x', tokens: 1 });
const html = renderHtml(r, { files: [tr], grade: grade(r), tips: tips(r), W });
assert.ok(!html.includes('</script><b>'), 'transcript text cannot close the script tag');
assert.strictEqual((html.match(/<\/script>/g) || []).length, 1);

fs.rmSync(tmp, { recursive: true });
console.log('hemat-token: all checks passed');
