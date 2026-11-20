#!/usr/bin/env python3
"""Cari skill yang cocok untuk sebuah pekerjaan.

  python3 cari_skill.py lokal  "analisa saham teknikal"      # skill yang sudah terpasang
  python3 cari_skill.py github "stock technical analysis"     # repo skill di GitHub, urut bintang

Hanya pustaka standar. Token opsional: GITHUB_TOKEN / GH_TOKEN (menaikkan batas rate API).
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

STOP = set(
    "dan atau yang untuk dengan di ke dari ini itu saya aku buat buatkan tolong bisa akan "
    "the and for with from that this into using use make please can"
    .split()
)
AKAR_DEFAULT = ["~/.claude/skills", "~/.claude/plugins", ".claude/skills"]


def kata(teks):
    return [w for w in re.findall(r"[a-z0-9]+", teks.lower()) if len(w) > 2 and w not in STOP]


def cocok(w, kumpulan):
    # shortcut: pencocokan 5 huruf awal sebagai pengganti stemming (analisa~analisis, saham~sahamnya)
    return any(w[:5] == d[:5] for d in kumpulan)


def baca_skill(path):
    teks = path.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"---\s*\n(.*?)\n---", teks, re.S)
    if not m:
        return None
    fm = m.group(1)
    nama = re.search(r"^name:\s*(.+)$", fm, re.M)
    # shortcut: deskripsi = teks setelah "description:" sampai kunci top-level berikutnya, bukan parser YAML penuh
    desk = re.search(r"^description:\s*(.*?)(?=^\S[^:\n]*:|\Z)", fm, re.M | re.S)
    if not nama:
        return None
    desk = re.sub(r"\s+", " ", desk.group(1)).replace('\\"', '"').strip(" >|\"'") if desk else ""
    return nama.group(1).strip().strip("\"'"), desk


def nama_plugin(path):
    for p in path.parents:
        manifest = p / ".claude-plugin" / "plugin.json"
        if manifest.is_file():
            try:
                return json.loads(manifest.read_text(encoding="utf-8")).get("name") or p.name
            except (ValueError, OSError):
                return p.name
    return None


def kumpulkan_skill(akar):
    hasil = {}
    for a in akar:
        root = Path(os.path.expanduser(a))
        if not root.is_dir():
            continue
        for f in root.rglob("SKILL.md"):
            info = baca_skill(f)
            if not info:
                continue
            nama, desk = info
            plugin = nama_plugin(f)
            sid = f"{plugin}:{nama}" if plugin else nama
            hasil.setdefault(sid, (desk, str(f)))
    return hasil


def skor(tugas, sid, desk):
    q = kata(tugas)
    if not q:
        return 0.0
    k_nama, k_desk = set(kata(sid.replace("-", " "))), set(kata(desk))
    nilai = sum(2 if cocok(w, k_nama) else 1 if cocok(w, k_desk) else 0 for w in q)
    return nilai / (2 * len(q))


def cmd_lokal(a):
    semua = kumpulkan_skill(AKAR_DEFAULT + a.dir)
    peringkat = sorted(((skor(a.tugas, s, d), s, d, p) for s, (d, p) in semua.items()), reverse=True)
    lolos = [r for r in peringkat if r[0] >= a.min][: a.top]
    print(f"# {len(semua)} skill terpasang dipindai untuk: {a.tugas!r}")
    if not lolos:
        print("TIDAK_ADA_SKILL_COCOK -> jalankan: cari_skill.py github \"<kata kunci Inggris>\"")
        return
    for s, sid, desk, path in lolos:
        print(f"\n[{s:.2f}] {sid}\n  {desk[:240]}\n  {path}")


def gh_search(q, n):
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": q, "sort": "stars", "order": "desc", "per_page": n}
    )
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "pengelola-skill"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("items", [])


def cmd_github(a):
    k = " ".join(kata(a.tugas)[:5])
    if not k:
        sys.exit("Kata kunci kosong. Contoh: cari_skill.py github \"stock technical analysis\"")
    kueri = [f"{k} topic:claude-skills", f"{k} topic:agent-skills", f"{k} claude skill", f"{k} skill", k]
    repo = {}
    for q in kueri:
        try:
            items = gh_search(q, a.top)
        except Exception as e:  # rate limit / jaringan: laporkan, lanjut kueri berikutnya
            print(f"! gagal '{q}': {e}", file=sys.stderr)
            continue
        for it in items:
            repo.setdefault(it["full_name"], (it, q))
        if len(repo) >= a.top:
            break
    if not repo:
        print("TIDAK_ADA_HASIL_GITHUB -> coba kata kunci Inggris lain yang lebih umum.")
        return
    urut = sorted(repo.values(), key=lambda x: x[0]["stargazers_count"], reverse=True)[: a.top]
    print(f"# Rekomendasi GitHub untuk {k!r} (urut bintang)")
    for i, (it, q) in enumerate(urut, 1):
        print(
            f"\n{i}. ★{it['stargazers_count']:,}  {it['full_name']}  (update {it['pushed_at'][:10]}, kueri: {q})\n"
            f"   {it['html_url']}\n   {(it.get('description') or '-')[:240]}"
        )


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    l = sub.add_parser("lokal", help="cocokkan pekerjaan dengan skill terpasang")
    l.add_argument("tugas")
    l.add_argument("--dir", action="append", default=[], help="folder tambahan berisi SKILL.md")
    l.add_argument("--top", type=int, default=8)
    l.add_argument("--min", type=float, default=0.25, help="skor minimum (0-1)")
    g = sub.add_parser("github", help="cari repo skill di GitHub, urut bintang")
    g.add_argument("tugas")
    g.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    (cmd_lokal if a.mode == "lokal" else cmd_github)(a)


if __name__ == "__main__":
    main()
