"""Tes mesin Generate: konteks, analog historis, pola, kerangka berpikir."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from insight import framework as fw
from insight.analogs import analog_stats, analog_table
from insight.context import context_at, feature_frame
from insight.patterns import matching, mine, wilson


def _raw(closes, start="2025-01-01", volume=1000.0):
    idx = pd.date_range(start, periods=len(closes), freq="D")
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": volume})


def test_context_buckets():
    up = _raw(np.linspace(100, 200, 300) + np.sin(np.arange(300)) * 0.5)
    down = _raw(np.linspace(200, 100, 300) + np.sin(np.arange(300)) * 0.5)
    assert context_at("BBCA.JK", up)["regime"] == "naik"
    assert context_at("AAPL", down)["regime"] == "turun"
    assert context_at("BTCUSDT", up)["pasar"] == "kripto"
    # konteks per tanggal lampau: sebelum 200 candle, regime belum bisa dihitung
    assert context_at("AAPL", up, when=date(2025, 3, 1))["regime"] is None
    assert feature_frame(up)["rsi"].iloc[-1] in ("kuat", "overbought")


def test_analogs_relax_keys():
    rng = np.random.default_rng(0)
    hist = {f"S{i}": _raw(100 * np.cumprod(1 + rng.normal(0.001, 0.01, 400))) for i in range(5)}
    table = analog_table(hist)
    assert len(table) > 900  # 5 simbol x (400 - 200 pemanasan MA200 - 5 horizon)
    assert {"fwd", "regime", "rsi"} <= set(table.columns)
    st = analog_stats(table, {"regime": "naik", "rsi": "kuat", "volatilitas": "normal", "volume": "normal"})
    assert st and st["n"] >= 30 and 0 <= st["peluang_naik"] <= 100 and st["p10"] <= st["median_return"] <= st["p90"]
    # konteks yang tak pernah ada -> kunci dilonggarkan sampai cukup sampel
    st2 = analog_stats(table, {"regime": "naik", "rsi": "tidak-ada"})
    assert st2["kunci"] == {"regime": "naik"}


def test_wilson_and_mining():
    lo, hi = wilson(8, 10)
    assert 0.4 < lo < 0.8 < hi <= 1
    recs = ([{"strategy": "A", "pnl": 2.0, "context": {"regime": "naik"}}] * 9 +
            [{"strategy": "A", "pnl": -1.0, "context": {"regime": "naik"}}] +
            [{"strategy": "A", "pnl": -2.0, "context": {"regime": "turun"}}] * 9 +
            [{"strategy": "B", "pnl": None, "context": {}}])
    m = mine(recs)
    assert m["total_pengalaman"] == 19
    good = [p for p in m["berhasil"] if p["kondisi"] == {"strategi": "A", "regime": "naik"}]
    bad = [p for p in m["gagal"] if p["kondisi"] == {"strategi": "A", "regime": "turun"}]
    assert good and good[0]["win_rate"] == 90 and bad and bad[0]["win_rate"] == 0
    mt = matching(m, {"regime": "turun"}, strategy="A")
    assert all(p["kondisi"].get("regime") in (None, "turun") for p in mt["gagal"] + mt["berhasil"])
    assert not any(p["kondisi"].get("regime") == "naik" for p in mt["berhasil"])


def _facts(regime="naik", rsi="kuat", sentiment=0.4):
    return {"simbol": "BBCA.JK", "harga": 1000.0, "perubahan_persen": 1.2,
            "konteks": {"regime": regime, "rsi": rsi, "rsi_value": 60.0, "volume": "tinggi"},
            "sentimen_berita": sentiment, "sinyal_aktif": [], "posisi": None}


def test_framework_bullish_vs_bearish():
    exp_up = {"analog": {"n": 400, "simbol": 20, "peluang_naik": 62.0, "median_return": 1.1, "p10": -3.0,
                         "p90": 5.0, "horizon_hari": 5}, "pola": {"berhasil": [], "gagal": []}}
    up = fw.build("peluang", _facts(), exp_up, {}, "Masuk BBCA?")
    assert up["hipotesis"]["ringkasan"]["bias"] == "bullish"
    assert up["keputusan"]["rekomendasi"]["operator"] in ("LAKUKAN", "BERTAHAP")
    buy = next(a for a in up["alternatif"] if a["operator"] == "LAKUKAN")
    assert buy["aksi"]["stop_loss"] == 970.0 and buy["aksi"]["take_profit"] == 1050.0
    assert len({a["operator"] for a in up["alternatif"]}) == 7  # semua operator pola pikir dibangkitkan

    exp_dn = {"analog": {**exp_up["analog"], "peluang_naik": 35.0}, "pola": {"berhasil": [], "gagal": []}}
    dn = fw.build("peluang", _facts("turun", "lemah", -0.4), exp_dn, {}, "Masuk BBCA?")
    assert dn["hipotesis"]["ringkasan"]["bias"] == "bearish"
    assert dn["keputusan"]["rekomendasi"]["operator"] in ("HINDARI", "TUNDA")
    bear = fw.build("peluang", _facts("turun", "lemah", -0.4),
                    {"analog": {**exp_up["analog"], "p10": -6.0, "p90": -0.5}, "pola": {"berhasil": [], "gagal": []}}, {}, "x")
    act = next(x for x in bear["alternatif"] if x["operator"] == "LAKUKAN")["aksi"]
    assert act["take_profit"] is None and act["stop_loss"] == 940.0
    assert "Rekomendasi" in fw.narrative(dn)


def test_operator_learning_moves_ranking():
    exp = {"analog": None, "pola": {"berhasil": [], "gagal": []}}
    base = fw.build("portofolio", {"portofolio": {"drawdown_persen": -1}}, exp, {}, "x")
    first = base["keputusan"]["rekomendasi"]["operator"]
    # operator lain yang berulang kali berhasil di masa lalu naik peringkat
    other = next(a["operator"] for a in base["alternatif"] if a["operator"] != first)
    learned = fw.build("portofolio", {"portofolio": {"drawdown_persen": -1}}, exp, {other: (40, 0), first: (0, 40)}, "x")
    assert learned["keputusan"]["rekomendasi"]["operator"] == other
    with pytest.raises(ValueError):
        fw.build("ngawur", {}, exp, {}, "x")


def test_strategy_case_recommends_disable_when_clearly_broken():
    exp = {"analog": None, "pola": {"berhasil": [], "gagal": [
        {"kondisi": {"strategi": "X", "regime": "turun"}, "n": 30, "win_rate": 10.0, "expectancy": -2.0,
         "wilson_bawah": 3.0, "wilson_atas": 25.0}]}}
    out = fw.build("strategi", {"strategi": "X", "strategi_stat": {"tertutup": 45, "win_rate": 30, "expectancy": -1.5}},
                   exp, {}, "X rugi terus")
    assert out["keputusan"]["rekomendasi"]["operator"] in ("HINDARI", "LINDUNGI")


def _fw_sample():
    exp = {"analog": {"n": 400, "simbol": 20, "peluang_naik": 62.0, "median_return": 1.1, "p10": -3.0,
                      "p90": 5.0, "horizon_hari": 5}, "pola": {"berhasil": [], "gagal": []}}
    return fw.build("peluang", _facts(), exp, {}, "Masuk BBCA?")


def test_llm_grounding_guard():
    from insight.llm import evidence_of, grounded
    ev = evidence_of(_fw_sample())
    assert grounded("Peluang naik 62% dalam 5 hari, median 1.1%.", ev)
    assert grounded("Harga 1000 dengan RSI 60.", ev)
    assert not grounded("Target harga 1350 dalam 3 hari.", ev)          # 1350 tidak ada di bukti
    assert not grounded("Peluang naik 87% menurut model.", ev)


def test_llm_narrate_with_stub_ollama(monkeypatch):
    import asyncio
    import json as _json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    from config import settings
    from insight import llm

    replies = iter(["BBCA condong naik: peluang naik 62% dalam 5 hari.", "Target 9999 pasti tercapai."])

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = _json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert body["stream"] is False and "BUKTI" in body["prompt"]
            out = _json.dumps({"response": next(replies)}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

        def log_message(self, *a):
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(settings, "ollama_url", f"http://127.0.0.1:{srv.server_address[1]}")
    sample = _fw_sample()
    try:
        text, src = asyncio.run(llm.narrate(sample))
        assert src.startswith("llm:") and "62%" in text
        text, src = asyncio.run(llm.narrate(sample))          # narasi mengarang angka -> ditolak
        assert "ditolak" in src and text == fw.narrative(sample)
    finally:
        srv.shutdown()
    monkeypatch.setattr(settings, "ollama_url", "http://127.0.0.1:9")  # tidak terjangkau -> template
    assert asyncio.run(llm.narrate(sample))[1] == "template (LLM tidak terjangkau)"


def test_auto_judge_and_symbol_resolution():
    from insight.service import judge, resolve_symbol

    class M:
        market_type_of = {"BBCA.JK": "indonesia", "ADAUSDT": "crypto", "NET": "us", "AAPL": "us"}
    assert judge("LAKUKAN", 3.0) == "berhasil" and judge("LAKUKAN", -1.0) == "gagal"
    assert judge("HINDARI", -2.0) == "berhasil" and judge("TUNDA", 5.0) == "gagal" and judge("RISET", 9) is None
    assert resolve_symbol(M, "apakah ada peluang di net hari ini") is None   # kata biasa bukan ticker
    assert resolve_symbol(M, "bagaimana BBCA minggu ini?") == "BBCA.JK"
    assert resolve_symbol(M, "ADA sedang turun") == "ADAUSDT"
    assert resolve_symbol(M, "bbca", explicit=True) == "BBCA.JK"


def test_analog_prefers_same_market():
    rng = np.random.default_rng(1)
    hist = {f"S{i}.JK": _raw(100 * np.cumprod(1 + rng.normal(0.001, 0.01, 400))) for i in range(4)}
    hist.update({f"C{i}USDT": _raw(100 * np.cumprod(1 + rng.normal(0.001, 0.03, 400))) for i in range(4)})
    table = analog_table(hist)
    st = analog_stats(table, {"pasar": "kripto", "regime": None, "rsi": None})
    assert st["kunci"] == {"pasar": "kripto"} and st["simbol"] == 4


def test_empty_portfolio_wording():
    out = fw.build("portofolio", {"portofolio": {"jumlah_posisi": 0, "drawdown_persen": 0}},
                   {"analog": None, "pola": {"berhasil": [], "gagal": []}}, {}, "x")
    assert out["keputusan"]["rekomendasi"]["judul"].startswith("Tetap kas")
