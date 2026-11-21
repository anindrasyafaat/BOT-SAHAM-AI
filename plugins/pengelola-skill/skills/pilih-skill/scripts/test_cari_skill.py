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


if __name__ == "__main__":
    test_lokal_peringkat_dan_nama_plugin()
    test_pengalaman_dan_evolusi()
    print("ok")
