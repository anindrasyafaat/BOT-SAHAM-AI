import tempfile
from pathlib import Path

import cari_skill as cs


def test_lokal_peringkat_dan_nama_plugin():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / ".claude-plugin").mkdir()
        (root / ".claude-plugin/plugin.json").write_text('{"name": "trading"}')
        for nama, desk in [("analisa-chart", "Analisa teknikal chart saham dan kripto."),
                           ("tulis-email", "Menulis email pemasaran.")]:
            (root / "skills" / nama).mkdir(parents=True)
            (root / "skills" / nama / "SKILL.md").write_text(
                f"---\nname: {nama}\ndescription: >\n  {desk}\nlicense: MIT\n---\nisi")
        semua = cs.kumpulkan_skill([d])
        assert set(semua) == {"trading:analisa-chart", "trading:tulis-email"}
        assert semua["trading:analisa-chart"][0] == "Analisa teknikal chart saham dan kripto."
        tugas = "buatkan analisis teknikal saham BBCA"
        assert cs.skor(tugas, "trading:analisa-chart", semua["trading:analisa-chart"][0]) >= 0.34
        assert cs.skor(tugas, "trading:tulis-email", semua["trading:tulis-email"][0]) == 0


def test_pengalaman_dan_evolusi():
    m = {"riwayat": [
            {"skill": "a:chart", "tugas": "analisa chart saham", "hasil": "berhasil"},
            {"skill": "b:jelek", "tugas": "analisa chart saham", "hasil": "gagal"},
            {"skill": "b:jelek", "tugas": "analisa chart emas", "hasil": "gagal"},
            {"skill": "b:jelek", "tugas": "analisa chart btc", "hasil": "gagal"}],
         "celah": [{"tugas": "optimasi query postgres"}, {"tugas": "query postgres lambat optimasi"},
                   {"tugas": "desain logo"}], "github": {}}
    exp = cs.pengalaman(m, "tolong analisa chart saham BBCA")
    assert exp["a:chart"] > 0 > exp["b:jelek"] >= -0.3
    assert "a:chart" not in cs.pengalaman(m, "desain logo")
    usulan, lemah, _ = cs.analisis_evolusi(m)
    assert [u["jumlah"] for u in usulan] == [2] and usulan[0]["nama"] == "optimasi-query-postgres"
    assert [w["skill"] for w in lemah] == ["b:jelek"]




def test_audit_memori_korup_dan_dashboard_aman():
    import json, os, subprocess, sys
    with tempfile.TemporaryDirectory() as d:
        mem = Path(d) / "memori.json"
        mem.write_text("{rusak json")                       # memori korup tidak boleh membuat crash
        env = {**os.environ, "PENGELOLA_SKILL_MEMORI": str(mem), "GITHUB_TOKEN": "ghp_RAHASIA_UJI"}
        run = lambda *a: subprocess.run([sys.executable, str(Path(__file__).parent / "cari_skill.py"), *a],
                                        env=env, capture_output=True, text=True, timeout=120)
        r = run("evolusi")
        assert r.returncode == 0, r.stderr
        r = run("catat", "x:y", "tugas </script><script>alert(1)</script>", "--hasil", "berhasil")
        assert r.returncode == 0 and json.loads(mem.read_text())["riwayat"]
        out = Path(d) / "dash.html"
        r = run("dashboard", "--out", str(out))
        html = out.read_text()
        # data pengguna tidak boleh menutup <script> lebih awal (XSS)
        assert "</script><script>alert(1)" not in html and "<\\/script>" in html
        r = run("github", "!!!")                            # kueri kosong -> keluar rapi
        assert r.returncode != 0 and "Kata kunci kosong" in (r.stderr + r.stdout)
        for x in (r.stdout, r.stderr):
            assert "ghp_RAHASIA_UJI" not in x                 # token tidak pernah dicetak


if __name__ == "__main__":
    test_lokal_peringkat_dan_nama_plugin()
    test_pengalaman_dan_evolusi()
    test_audit_memori_korup_dan_dashboard_aman()
    print("ok")
