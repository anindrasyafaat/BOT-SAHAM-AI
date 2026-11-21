"""Gerbang kualitas: preflight sebelum generate, review sebelum menjawab."""

import copy

from insight import framework as fw
from insight.quality import position_size, preflight, review, robustness

GOOD_META = {"umur_data_detik": 30, "interval": 60, "harga": 1000.0, "candle": 250, "lonjakan_maks_persen": 3.0,
             "high_low_terbalik": False, "analog_n": 120, "berita": 5, "pengalaman": 40, "akurasi_ml": 0.55}


def status(rep, id_):
    return next(c["status"] for c in rep["checks"] if c["id"] == id_)


def test_preflight_passes_clean_data():
    rep = preflight("peluang", GOOD_META)
    assert rep["verdict"] == "lulus" and not rep["blocking"]


def test_preflight_blocks_and_warns():
    assert preflight("peluang", {**GOOD_META, "umur_data_detik": None})["blocking"]
    assert preflight("peluang", {**GOOD_META, "candle": 30})["blocking"]
    assert preflight("peluang", {**GOOD_META, "harga": float("nan")})["blocking"]
    assert preflight("peluang", {**GOOD_META, "high_low_terbalik": True})["blocking"]
    stale = preflight("peluang", {**GOOD_META, "umur_data_detik": 600})
    assert status(stale, "kesegaran") == "peringatan" and not stale["blocking"]
    dead = preflight("peluang", {**GOOD_META, "umur_data_detik": 8 * 3600, "error_terakhir": "timeout"})
    assert dead["blocking"]
    assert status(preflight("peluang", {**GOOD_META, "candle": 150}), "candle") == "peringatan"
    assert status(preflight("peluang", {**GOOD_META, "lonjakan_maks_persen": 40}), "anomali") == "peringatan"
    thin = preflight("peluang", {**GOOD_META, "analog_n": None, "berita": 0, "pengalaman": 3, "akurasi_ml": None})
    assert thin["verdict"] == "lulus dengan catatan"
    blocked = preflight("peluang", {**GOOD_META, "candle": 10})
    assert all(c["perbaikan"] for c in blocked["checks"] if c["status"] == "gagal")  # selalu ada cara memperbaiki


def _bull_fw():
    facts = {"simbol": "BBCA.JK", "harga": 1000.0, "perubahan_persen": 1.2,
             "konteks": {"regime": "naik", "rsi": "kuat", "rsi_value": 60.0, "volume": "tinggi"},
             "sentimen_berita": 0.4, "sinyal_aktif": [], "posisi": None}
    exp = {"analog": {"n": 400, "simbol": 20, "peluang_naik": 62.0, "median_return": 1.1, "p10": -3.0, "p90": 5.0,
                      "horizon_hari": 5}, "pola": {"berhasil": [], "gagal": []}}
    rebuild = lambda ex: fw.build("peluang", facts, exp, {}, "x", exclude=ex)
    return rebuild(frozenset()), rebuild


def _review(f, rebuild, **kw):
    args = dict(operator_stats={}, capital=100_000_000, cash=100_000_000, risk_per_trade=0.02, fx=1.0)
    args.update(kw)
    return review(f, rebuild, **args)


def test_review_consistent_decision_is_kept():
    f, rebuild = _bull_fw()
    r = _review(f, rebuild)
    assert not r["diturunkan"] and r["keputusan_final"]["operator"] == f["keputusan"]["rekomendasi"]["operator"]
    assert r["stabilitas"] is not None and 0 <= r["keyakinan"] <= 100
    assert status(r, "arah") == "lulus" and status(r, "level") == "lulus"
    assert r["ukuran_posisi"]["jumlah_maks"] % 100 == 0                     # lot IDX


def test_review_downgrades_inconsistent_or_broken_levels():
    f, rebuild = _bull_fw()
    bad = copy.deepcopy(f)
    bad["hipotesis"]["ringkasan"]["bias"] = "bearish"                        # beli padahal bukti turun
    bad["keputusan"]["rekomendasi"] = next(a for a in bad["alternatif"] if a["operator"] == "LAKUKAN")
    r = _review(bad, rebuild)
    assert status(r, "arah") == "gagal" and r["diturunkan"]
    assert r["keputusan_final"]["operator"] in ("TUNDA", "RISET") and r["keputusan_final"]["alasan_kontrol"]

    lvl = copy.deepcopy(f)
    lvl["keputusan"]["rekomendasi"] = next(a for a in lvl["alternatif"] if a["operator"] == "LAKUKAN")
    lvl["keputusan"]["rekomendasi"]["aksi"]["stop_loss"] = 1200.0             # SL di atas harga
    r = _review(lvl, rebuild)
    assert status(r, "level") == "gagal" and r["diturunkan"]


def test_robustness_detects_fragile_decision():
    f, _ = _bull_fw()
    assert robustness(f, lambda ex: f) == (100, [])
    fragile_key = f["hipotesis"]["bukti"][0]["teks"]
    flipped = copy.deepcopy(f)
    flipped["keputusan"]["rekomendasi"] = {**flipped["keputusan"]["rekomendasi"], "operator": "HINDARI"}
    stab, flippers = robustness(f, lambda ex: flipped if fragile_key in ex else f)
    assert stab < 100 and flippers == [fragile_key]
    every = robustness(f, lambda ex: flipped)[0]
    assert every == 0
    r = _review(f, lambda ex: flipped)                                       # rapuh total -> keyakinan rendah -> turun
    assert status(r, "ketahanan") == "peringatan" and r["keyakinan"] < 60


def test_position_size():
    s = position_size(1000, 970, 1.0, 100_000_000, 100_000_000, 0.02, idx=True)
    assert s["jumlah_maks"] == 66600 and not s["dibatasi_kas"] and s["risiko_idr"] <= 2_000_000
    s = position_size(1000, 970, 1.0, 100_000_000, 10_000_000, 0.02, idx=True)
    assert s["jumlah_maks"] == 10000 and s["dibatasi_kas"]
    assert position_size(1000, None, 1.0, 1e8, 1e8, 0.02, idx=True) is None
    assert position_size(1000, 1100, 1.0, 1e8, 1e8, 0.02, idx=True) is None  # SL di atas harga


def test_preflight_warnings_lower_confidence():
    f, rebuild = _bull_fw()
    clean = _review(f, rebuild)["keyakinan"]
    warned = _review(f, rebuild, pre_checks=preflight("peluang", {**GOOD_META, "candle": 150, "berita": 0})["checks"])
    assert warned["keyakinan"] < clean


def test_devils_advocate_matches_decision_direction():
    f, rebuild = _bull_fw()
    for op, want in (("LAKUKAN", lambda b: b < 0), ("HINDARI", lambda b: b > 0), ("TUNDA", lambda b: b != 0)):
        g = copy.deepcopy(f)
        g["keputusan"]["rekomendasi"] = next(a for a in g["alternatif"] if a["operator"] == op)
        devil = _review(g, lambda ex: g)["advokat_setan"]
        weights = {e["teks"]: e["bobot"] for e in g["hipotesis"]["bukti"]}
        listed = [t for t in devil if t in weights]
        assert all(want(weights[t]) for t in listed), (op, listed)
        if op == "TUNDA":
            top = max(g["hipotesis"]["bukti"], key=lambda e: abs(e["bobot"]))["teks"]
            assert listed and listed[0] == top
