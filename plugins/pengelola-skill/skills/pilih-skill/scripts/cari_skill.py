#!/usr/bin/env python3
"""Cari skill yang cocok untuk sebuah pekerjaan.

  python3 cari_skill.py lokal  "analisa saham teknikal"      # skill yang sudah terpasang
  python3 cari_skill.py github "stock technical analysis"     # repo skill di GitHub, urut bintang
  python3 cari_skill.py catat god-mode-trading:analisa-chart "analisa saham BBCA" --hasil berhasil
  python3 cari_skill.py evolusi                                # celah berulang -> usulan skill baru
  python3 cari_skill.py dashboard                              # dashboard HTML

Memori belajar: ~/.claude/pengelola-skill/memori.json (ubah lewat env PENGELOLA_SKILL_MEMORI).

Hanya pustaka standar. Token opsional: GITHUB_TOKEN / GH_TOKEN (menaikkan batas rate API).
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

STOP = set(
    "dan atau yang untuk dengan di ke dari ini itu saya aku buat buatkan tolong bisa akan "
    "the and for with from that this into using use make please can"
    .split()
)
AKAR_DEFAULT = ["~/.claude/skills", "~/.claude/plugins", ".claude/skills"]
MEMORI = Path(os.environ.get("PENGELOLA_SKILL_MEMORI", "~/.claude/pengelola-skill/memori.json")).expanduser()


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


# ---------- memori belajar ----------

def muat():
    try:
        m = json.loads(MEMORI.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        m = {}
    for k, v in (("riwayat", []), ("celah", []), ("github", {})):
        m.setdefault(k, v)
    return m


def simpan(m):
    MEMORI.parent.mkdir(parents=True, exist_ok=True)
    tmp = MEMORI.with_suffix(".tmp")
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(MEMORI)  # atomik: memori lama tidak rusak bila proses terhenti


def sekarang():
    return datetime.now().isoformat(timespec="seconds")


def mirip(a, b):
    qa, kb = kata(a), set(kata(b))
    return sum(cocok(w, kb) for w in qa) / len(qa) if qa else 0.0


def pengalaman(m, tugas):
    """Skor pengalaman per skill: catatan berhasil/gagal pada tugas mirip menggeser peringkat (maks ±0.3)."""
    hasil = {}
    for r in m["riwayat"]:
        k = mirip(tugas, r["tugas"])
        if k >= 0.5:
            hasil[r["skill"]] = hasil.get(r["skill"], 0) + (0.15 if r["hasil"] == "berhasil" else -0.15) * k
    return {s: max(-0.3, min(0.3, b)) for s, b in hasil.items()}


def cmd_lokal(a):
    semua = kumpulkan_skill(AKAR_DEFAULT + a.dir)
    m = muat()
    exp = pengalaman(m, a.tugas)
    peringkat = sorted(((skor(a.tugas, s, d) + exp.get(s, 0), s, d, p) for s, (d, p) in semua.items()), reverse=True)
    lolos = [r for r in peringkat if r[0] >= a.min][: a.top]
    print(f"# {len(semua)} skill terpasang dipindai untuk: {a.tugas!r}")
    di_luar = {s: b for s, b in exp.items() if b > 0 and s not in semua}
    for s, b in sorted(di_luar.items(), key=lambda x: -x[1]):
        print(f"\n[pengalaman +{b:.2f}] {s}  (pernah berhasil untuk tugas mirip; skill bawaan/tak ada di disk)")
    if not lolos and not di_luar:
        m["celah"].append({"tugas": a.tugas, "waktu": sekarang()})
        simpan(m)
        print("TIDAK_ADA_SKILL_COCOK (dicatat sebagai celah) -> jalankan: cari_skill.py github \"<kata kunci Inggris>\"")
        return
    for s, sid, desk, path in lolos:
        tanda = f" (pengalaman {exp[sid]:+.2f})" if exp.get(sid) else ""
        print(f"\n[{s:.2f}] {sid}{tanda}\n  {desk[:240]}\n  {path}")


def cmd_catat(a):
    m = muat()
    m["riwayat"].append({"skill": a.skill, "tugas": a.tugas, "hasil": a.hasil, "catatan": a.catatan, "waktu": sekarang()})
    if a.hasil == "berhasil":  # celah yang kini terjawab tidak perlu diusulkan lagi
        m["celah"] = [c for c in m["celah"] if mirip(c["tugas"], a.tugas) < 0.6]
    simpan(m)
    print(f"Tercatat: {a.skill} -> {a.hasil} untuk {a.tugas!r} ({len(m['riwayat'])} catatan di {MEMORI})")


def slug(teks):
    return "-".join(kata(teks)[:3]) or "skill-baru"


def analisis_evolusi(m):
    """Kelompokkan celah yang berulang (usulan skill baru) dan temukan skill yang sering gagal."""
    sisa, usulan = list(m["celah"]), []
    while sisa:
        dasar = sisa.pop(0)
        grup = [dasar] + [c for c in sisa if mirip(dasar["tugas"], c["tugas"]) >= 0.5]
        sisa = [c for c in sisa if c not in grup]
        if len(grup) >= 2:
            usulan.append({"nama": slug(dasar["tugas"]), "jumlah": len(grup), "tugas": [g["tugas"] for g in grup]})
    statistik = {}
    for r in m["riwayat"]:
        st = statistik.setdefault(r["skill"], [0, 0])
        st[0 if r["hasil"] == "berhasil" else 1] += 1
    lemah = [{"skill": s, "berhasil": b, "gagal": g} for s, (b, g) in statistik.items() if b + g >= 3 and b < g]
    return sorted(usulan, key=lambda u: -u["jumlah"]), lemah, statistik


def cmd_evolusi(a):
    usulan, lemah, _ = analisis_evolusi(muat())
    if not usulan and not lemah:
        print("Belum ada pola. Evolusi butuh celah berulang (>=2 tugas mirip tanpa skill) atau skill yang sering gagal.")
        return
    for u in usulan:
        print(f"\nUSULAN_SKILL_BARU: {u['nama']}  ({u['jumlah']}x diminta tanpa skill)")
        for t in u["tugas"]:
            print(f"  - {t}")
        print(f"  -> buat ~/.claude/skills/{u['nama']}/SKILL.md (pakai skill-creator) atau pasang dari GitHub")
    for w in lemah:
        print(f"\nSKILL_LEMAH: {w['skill']}  berhasil {w['berhasil']} / gagal {w['gagal']} -> cari pengganti atau perbaiki")


def gh_search(q, n):
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": q, "sort": "stars", "order": "desc", "per_page": n}
    )
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "pengelola-skill"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:  # nosec B310 - URL konstanta https://api.github.com
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
    m = muat()
    m["github"][k] = {"waktu": sekarang(), "repo": [
        {"nama": it["full_name"], "bintang": it["stargazers_count"], "url": it["html_url"],
         "update": it["pushed_at"][:10], "deskripsi": (it.get("description") or "")[:240]} for it, _ in urut]}
    simpan(m)
    print(f"# Rekomendasi GitHub untuk {k!r} (urut bintang)")
    for i, (it, q) in enumerate(urut, 1):
        print(
            f"\n{i}. ★{it['stargazers_count']:,}  {it['full_name']}  (update {it['pushed_at'][:10]}, kueri: {q})\n"
            f"   {it['html_url']}\n   {(it.get('description') or '-')[:240]}"
        )


def cmd_dashboard(a):
    semua = kumpulkan_skill(AKAR_DEFAULT + a.dir)
    m = muat()
    usulan, lemah, statistik = analisis_evolusi(m)
    data = {
        "dibuat": sekarang(), "stop": sorted(STOP),
        "skill": [{"id": s, "desk": d} for s, (d, _) in sorted(semua.items())],
        "riwayat": m["riwayat"], "celah": m["celah"], "github": m["github"],
        "usulan": usulan, "lemah": lemah,
        "statistik": [{"skill": s, "berhasil": b, "gagal": g} for s, (b, g) in statistik.items()],
    }
    template = (Path(__file__).parent / "dashboard.html").read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")  # cegah penutupan <script> dini
    out = Path(a.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(template.replace("__DATA__", blob), encoding="utf-8")
    print(f"Dashboard: {out}  ({len(semua)} skill, {len(m['riwayat'])} catatan, {len(usulan)} usulan evolusi)")


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
    c = sub.add_parser("catat", help="catat hasil pemakaian skill (bahan belajar)")
    c.add_argument("skill")
    c.add_argument("tugas")
    c.add_argument("--hasil", choices=["berhasil", "gagal"], required=True)
    c.add_argument("--catatan", default="")
    sub.add_parser("evolusi", help="usulkan skill baru dari celah berulang & tandai skill lemah")
    d = sub.add_parser("dashboard", help="buat dashboard HTML")
    d.add_argument("--out", default=str(MEMORI.parent / "dashboard.html"))
    d.add_argument("--dir", action="append", default=[])
    a = ap.parse_args()
    {"lokal": cmd_lokal, "github": cmd_github, "catat": cmd_catat, "evolusi": cmd_evolusi, "dashboard": cmd_dashboard}[a.mode](a)


if __name__ == "__main__":
    import signal
    if hasattr(signal, "SIGPIPE"):  # keluar diam-diam saat output di-pipe ke `head`
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
