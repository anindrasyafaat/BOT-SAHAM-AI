// Renders the token audit as one self-contained HTML file (no network, no dependencies).
// Data goes in as JSON; the page draws SVG charts with hover tooltips and table views.

function renderHtml(r, { files, grade, tips, W }) {
  const data = { r, files: files.map((f) => f.split(/[\\/]/).pop()), grade, tips, W, at: new Date().toISOString() };
  // `<` escaped so tool labels like "</script>" in the transcript cannot break out of the script tag
  const json = JSON.stringify(data).replace(/</g, '\\u003c');
  return `<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audit Token</title>
<style>
:root {
  color-scheme: light;
  --page: #f4f4f2; --surface-1: #fcfcfb; --border: #e4e3df; --grid: #e4e3df;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #75746f;
  --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a; --series-4: #eda100;
  --good: #0ca30c; --good-text: #006300; --warning: #fab219; --critical: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --page: #111110; --surface-1: #1a1a19; --border: #2c2c2a; --grid: #2c2c2a;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #9a998f;
    --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500;
    --good: #0ca30c; --good-text: #0ca30c; --warning: #fab219; --critical: #d03b3b;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #111110; --surface-1: #1a1a19; --border: #2c2c2a; --grid: #2c2c2a;
  --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #9a998f;
  --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500;
  --good: #0ca30c; --good-text: #0ca30c; --warning: #fab219; --critical: #d03b3b;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--text-primary);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1040px; margin: 0 auto; padding: 32px 16px 48px; }
h1 { font-size: 26px; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 16px; margin: 0 0 2px; }
.sub { color: var(--text-secondary); margin: 0 0 24px; font-size: 14px; overflow-wrap: anywhere; }
.desc { color: var(--text-secondary); font-size: 13px; margin: 0 0 14px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px; }
.kpi .label { color: var(--text-secondary); font-size: 13px; }
.kpi .value { font-size: 28px; font-weight: 650; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.kpi .note { color: var(--text-muted); font-size: 12px; }
.kpi.hero .value { font-size: 40px; }
.badge { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; padding: 2px 10px;
  border-radius: 999px; border: 1px solid var(--border); color: var(--text-primary); }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; flex: none; }
.grid2 { display: grid; grid-template-columns: 1fr; gap: 16px; margin-bottom: 16px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 13px; color: var(--text-secondary); margin-bottom: 10px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
svg { display: block; width: 100%; height: auto; overflow: visible; }
svg text { fill: var(--text-secondary); font-size: 12px; font-variant-numeric: tabular-nums; }
svg .val { fill: var(--text-primary); font-weight: 600; }
.hit { fill: transparent; cursor: default; }
.col:hover > :not(.hit) { opacity: 0.78; }
details { margin-top: 12px; font-size: 13px; }
summary { cursor: pointer; color: var(--text-secondary); }
.tablewrap { overflow-x: auto; max-height: 320px; margin-top: 8px; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { text-align: right; padding: 4px 10px; border-bottom: 1px solid var(--border); white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--text-secondary); font-weight: 600; position: sticky; top: 0; background: var(--surface-1); }
.tools { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.tools li { display: grid; grid-template-columns: minmax(0, 1fr) 72px; gap: 4px 12px; align-items: center; }
.tools .name { font: 12.5px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--text-primary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tools .num { text-align: right; font-variant-numeric: tabular-nums; color: var(--text-primary); font-weight: 600; font-size: 13px; }
.tools .track { grid-column: 1 / -1; height: 6px; }
.tools .bar { height: 6px; border-radius: 0 4px 4px 0; background: var(--series-1); min-width: 2px; }
.fix { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.fix li { display: flex; gap: 10px; align-items: flex-start; }
.fix .tag { flex: none; font-size: 12px; font-weight: 600; padding: 1px 8px; border-radius: 6px; border: 1px solid var(--border); }
.empty { color: var(--text-muted); font-size: 13px; }
footer { color: var(--text-muted); font-size: 12px; margin-top: 8px; }
#tip { position: fixed; pointer-events: none; z-index: 10; background: var(--surface-1); color: var(--text-primary);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; font-size: 12.5px; line-height: 1.5;
  box-shadow: 0 6px 24px rgb(0 0 0 / 0.18); opacity: 0; transition: opacity .08s; max-width: 280px; }
#tip b { font-variant-numeric: tabular-nums; }
@media (min-width: 860px) { .grid2 { grid-template-columns: 1fr 1fr; } }
@media (forced-colors: active) { .tools .bar, .dot, .legend i { forced-color-adjust: none; } }
</style>
</head>
<body>
<main>
  <h1>Audit Token</h1>
  <p class="sub" id="sub"></p>
  <section class="kpis" id="kpis" aria-label="Ringkasan"></section>

  <section class="card" style="margin-bottom:16px">
    <h2>Komposisi biaya</h2>
    <p class="desc">Biaya berbobot dalam token-setara input. Cache read dibayar 0,1x, sehingga batang aktual jauh lebih pendek dibanding tanpa cache.</p>
    <div class="legend" id="legend-cost"></div>
    <div id="cost"></div>
    <details><summary>Lihat tabel</summary><div class="tablewrap" id="cost-table"></div></details>
  </section>

  <section class="card" style="margin-bottom:16px">
    <h2>Konteks per panggilan API</h2>
    <p class="desc">Token input yang dikirim di setiap panggilan. Makin dominan cache read, makin murah. Batang yang tumbuh cepat berarti konteks membengkak.</p>
    <div class="legend" id="legend-calls"></div>
    <div id="calls"></div>
    <details><summary>Lihat tabel</summary><div class="tablewrap" id="calls-table"></div></details>
  </section>

  <div class="grid2">
    <section class="card">
      <h2>Hasil tool terbesar</h2>
      <p class="desc">Perkiraan token yang masuk ke konteks dan terbawa sampai akhir sesi.</p>
      <ul class="tools" id="tools"></ul>
    </section>
    <section class="card">
      <h2>Perbaiki berikutnya</h2>
      <p class="desc">Diambil dari pola sesi ini.</p>
      <ul class="fix" id="fix"></ul>
    </section>
  </div>
  <footer id="foot"></footer>
</main>
<div id="tip" role="tooltip"></div>
<script>
const D = ${json};
const r = D.r, W = D.W;
const nf = new Intl.NumberFormat('id-ID', { notation: 'compact', maximumFractionDigits: 1 });
const full = new Intl.NumberFormat('id-ID');
const pct = (x) => (x * 100).toLocaleString('id-ID', { maximumFractionDigits: 1 }) + '%';
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const NS = 'http://www.w3.org/2000/svg';
const el = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };

// Series: colour follows the entity everywhere on the page.
const S = [
  { key: 'uncached', name: 'Input tanpa cache', color: 'var(--series-1)' },
  { key: 'write', name: 'Cache write', color: 'var(--series-2)' },
  { key: 'read', name: 'Cache read', color: 'var(--series-3)' },
  { key: 'output', name: 'Output', color: 'var(--series-4)' },
];
const legend = (id, keys) => { $(id).innerHTML = S.filter((s) => keys.includes(s.key)).map((s) => '<span><i style="background:' + s.color + '"></i>' + s.name + '</span>').join(''); };

// Tooltip
const tip = $('tip');
document.addEventListener('pointermove', (e) => {
  const t = e.target.closest('[data-tip]');
  if (!t) { tip.style.opacity = 0; return; }
  tip.innerHTML = t.getAttribute('data-tip');
  const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.min(e.clientX + pad, innerWidth - w - 8) + 'px';
  tip.style.top = (e.clientY + pad + h > innerHeight ? e.clientY - h - pad : e.clientY + pad) + 'px';
  tip.style.opacity = 1;
});

// Bar shape with only the data end rounded (right for horizontal, top for vertical)
function endRounded(x, y, w, h, rad, dir) {
  rad = Math.max(0, Math.min(rad, dir === 'h' ? w : h, dir === 'h' ? h / 2 : w / 2));
  if (dir === 'h') return 'M' + x + ',' + y + 'h' + (w - rad) + 'a' + rad + ',' + rad + ' 0 0 1 ' + rad + ',' + rad + 'v' + (h - 2 * rad) + 'a' + rad + ',' + rad + ' 0 0 1 ' + -rad + ',' + rad + 'h' + -(w - rad) + 'z';
  return 'M' + x + ',' + (y + h) + 'v' + -(h - rad) + 'a' + rad + ',' + rad + ' 0 0 1 ' + rad + ',' + -rad + 'h' + (w - 2 * rad) + 'a' + rad + ',' + rad + ' 0 0 1 ' + rad + ',' + rad + 'v' + (h - rad) + 'z';
}
function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= v) return m * p; return 10 * p; }

// Header + KPIs
$('sub').textContent = 'Transkrip: ' + D.files.join(', ') + ' · dibuat ' + new Date(D.at).toLocaleString('id-ID');
const gradeStatus = { A: ['var(--good)', 'Sangat hemat'], B: ['var(--warning)', 'Cukup hemat'], C: ['var(--warning)', 'Perlu perbaikan'], D: ['var(--critical)', 'Boros'] }[D.grade];
const kpis = [
  ['hero', 'Penghematan vs tanpa cache', pct(r.saving), '<span class="badge"><span class="dot" style="background:' + gradeStatus[0] + '"></span>Nilai ' + D.grade + ' · ' + gradeStatus[1] + '</span>'],
  ['', 'Cache hit rate', pct(r.cacheHitRate), 'dari ' + nf.format(r.allInput) + ' token input'],
  ['', 'Biaya berbobot', nf.format(r.weightedActual), 'vs ' + nf.format(r.weightedNoCache) + ' tanpa cache'],
  ['', 'Panggilan API', full.format(r.calls), 'output ' + nf.format(r.output) + ' token'],
];
$('kpis').innerHTML = kpis.map(([cls, l, v, n]) => '<div class="card kpi ' + cls + '"><div class="label">' + l + '</div><div class="value">' + v + '</div><div class="note">' + n + '</div></div>').join('');

// Charts draw at the container's real pixel width so text stays 12px on phone and desktop
legend('legend-cost', ['uncached', 'write', 'read', 'output']);
legend('legend-calls', ['uncached', 'write', 'read']);

// Cost composition: actual vs no-cache on one shared scale
function drawCost() {
  $('cost').innerHTML = '';
  const rows = [
    { name: 'Aktual', parts: { uncached: r.input * W.input, write: r.write5m * W.write5m + r.write1h * W.write1h, read: r.read * W.read, output: r.output * W.output } },
    { name: 'Tanpa cache', parts: { uncached: r.allInput * W.input, write: 0, read: 0, output: r.output * W.output } },
  ];
  const VW = $('cost').clientWidth || 640, L = VW < 480 ? 80 : 96, R = 64, BH = 26, GAP = 18, H = rows.length * (BH + GAP);
  const max = Math.max(...rows.map((row) => Object.values(row.parts).reduce((a, b) => a + b, 0))) || 1;
  const sx = (v) => (v / max) * (VW - L - R);
  const svg = el('svg', { viewBox: '0 0 ' + VW + ' ' + H, role: 'img', 'aria-label': 'Komposisi biaya aktual vs tanpa cache' }, $('cost'));
  rows.forEach((row, i) => {
    const y = i * (BH + GAP) + 4;
    el('text', { x: 0, y: y + BH / 2 + 4 }, svg).textContent = row.name;
    const segs = S.map((s) => ({ s, v: row.parts[s.key] })).filter((p) => p.v > 0);
    const total = segs.reduce((a, p) => a + p.v, 0);
    let x = L;
    segs.forEach((p, j) => {
      const w = sx(p.v), last = j === segs.length - 1, drawW = Math.max(1, last ? w : w - 2);
      const tipHtml = '<b>' + row.name + ' · ' + p.s.name + '</b><br>' + full.format(Math.round(p.v)) + ' token-setara (' + pct(p.v / total) + ')';
      if (last) el('path', { d: endRounded(x, y, drawW, BH, 4, 'h'), fill: p.s.color, 'data-tip': tipHtml }, svg);
      else el('rect', { x, y, width: drawW, height: BH, fill: p.s.color, 'data-tip': tipHtml }, svg);
      x += w;
    });
    const t = el('text', { x: x + 8, y: y + BH / 2 + 4, class: 'val' }, svg); t.textContent = nf.format(total);
  });
  $('cost-table').innerHTML = '<table><tr><th>Baris</th>' + S.map((s) => '<th>' + s.name + '</th>').join('') + '<th>Total</th></tr>' +
    rows.map((row) => { const tot = Object.values(row.parts).reduce((a, b) => a + b, 0); return '<tr><td>' + row.name + '</td>' + S.map((s) => '<td>' + full.format(Math.round(row.parts[s.key])) + '</td>').join('') + '<td>' + full.format(Math.round(tot)) + '</td></tr>'; }).join('') + '</table>';
}

// Context per API call: stacked columns
function drawCalls() {
  $('calls').innerHTML = '';
  const calls = r.perCall;
  if (!calls.length) { $('calls').innerHTML = '<p class="empty">Tidak ada panggilan API di transkrip ini.</p>'; return; }
  const VW = $('calls').clientWidth || 640, H = VW < 480 ? 180 : 240, L = 52, B = 22, T = 8, PW = VW - L - 4, PH = H - B - T;
  const keys = ['uncached', 'write', 'read'];
  const max = niceMax(Math.max(...calls.map((c) => c.uncached + c.write + c.read)));
  const sy = (v) => (v / max) * PH;
  const svg = el('svg', { viewBox: '0 0 ' + VW + ' ' + H, role: 'img', 'aria-label': 'Token input per panggilan API' }, $('calls'));
  for (let i = 0; i <= 4; i++) {
    const v = (max / 4) * i, y = T + PH - sy(v);
    el('line', { x1: L, x2: VW, y1: y, y2: y, stroke: 'var(--grid)', 'stroke-width': 1 }, svg);
    const t = el('text', { x: L - 6, y: y + 4, 'text-anchor': 'end' }, svg); t.textContent = nf.format(v);
  }
  const cw = PW / calls.length, gap = cw > 6 ? 2 : 0, bw = Math.max(0.6, cw - gap);
  calls.forEach((c, i) => {
    const g = el('g', { class: 'col' }, svg), x = L + 2 + i * cw;
    let y = T + PH;
    const present = keys.filter((k) => c[k] > 0);
    present.forEach((k, j) => {
      const h = sy(c[k]), top = j === present.length - 1, drawH = top ? h : Math.max(0, h - (gap ? 1 : 0));
      const s = S.find((q) => q.key === k);
      if (top) el('path', { d: endRounded(x, y - h, bw, h, Math.min(4, bw / 2), 'v'), fill: s.color }, g);
      else el('rect', { x, y: y - drawH, width: bw, height: drawH, fill: s.color }, g);
      y -= h;
    });
    const tipHtml = '<b>Panggilan #' + (i + 1) + '</b><br>' + S.filter((s) => s.key !== 'output').map((s) => '<span class="dot" style="background:' + s.color + '"></span> ' + s.name + ': <b>' + full.format(c[s.key]) + '</b>').join('<br>') + '<br>Output: <b>' + full.format(c.output) + '</b>';
    el('rect', { x: x - gap / 2, y: T, width: cw, height: PH, class: 'hit', 'data-tip': tipHtml }, g);
  });
  const step = Math.max(1, Math.ceil(calls.length / Math.max(3, Math.floor(PW / 70))));
  for (let i = 0; i < calls.length; i += step) { const t = el('text', { x: L + 2 + i * cw + bw / 2, y: H - 4, 'text-anchor': 'middle' }, svg); t.textContent = '#' + (i + 1); }
  $('calls-table').innerHTML = '<table><tr><th>Panggilan</th>' + S.map((s) => '<th>' + s.name + '</th>').join('') + '</tr>' +
    calls.map((c, i) => '<tr><td>#' + (i + 1) + '</td>' + S.map((s) => '<td>' + full.format(c[s.key]) + '</td>').join('') + '</tr>').join('') + '</table>';
}
drawCost(); drawCalls();
let rz; addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { drawCost(); drawCalls(); }, 120); });

// Biggest tool results
(function () {
  const list = r.topToolResults || [];
  if (!list.length) { $('tools').innerHTML = '<li class="empty">Tidak ada hasil tool.</li>'; return; }
  const max = list[0].tokens || 1;
  $('tools').innerHTML = list.map((t) => '<li><span class="name" title="' + esc(t.label) + '">' + esc(t.label) + '</span><span class="num">' + nf.format(t.tokens) + '</span><div class="track"><div class="bar" style="width:' + (t.tokens / max * 100).toFixed(1) + '%"></div></div></li>').join('');
})();

// Fix list: status colour always paired with a text tag
$('fix').innerHTML = D.tips.length
  ? D.tips.map((t) => '<li><span class="tag"><span class="dot" style="background:var(--warning)"></span> Perbaiki</span><span>' + esc(t) + '</span></li>').join('')
  : '<li><span class="tag"><span class="dot" style="background:var(--good)"></span> Aman</span><span>Tidak ada kebocoran token yang terdeteksi.</span></li>';

$('foot').textContent = 'Bobot harga relatif ke 1 token input: cache read ' + full.format(W.read) + 'x, cache write ' + full.format(W.write5m) + 'x (5 menit) / ' + full.format(W.write1h) + 'x (1 jam), output ' + full.format(W.output) + 'x. Token hasil tool diperkirakan dari jumlah karakter / 4.';
</script>
</body>
</html>
`;
}

module.exports = { renderHtml };
