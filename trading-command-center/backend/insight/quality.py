"""
Gerbang kualitas fitur Generate.

Gerbang 1 — preflight (SEBELUM generate): apakah data & pengalaman cukup dan sehat untuk berpikir?
  'gagal'      -> generate diblokir, dengan langkah perbaikan
  'peringatan' -> generate jalan, keyakinan dikurangi
Gerbang 2 — review (SEBELUM menjawab): apakah keputusan konsisten, wajar, tahan uji, dan risikonya terkendali?
  Bila ada 'gagal' atau keyakinan terlalu rendah, rekomendasi DITURUNKAN ke TUNDA/RISET (yang asli tetap terlihat).

Semua fungsi murni; data dikumpulkan oleh insight/service.py.
"""

import math
from typing import Callable, Dict, List, Optional, Tuple

from signals.learning import valid_levels

LULUS, PERINGATAN, GAGAL = "lulus", "peringatan", "gagal"
DIRECTION = {"LAKUKAN": 1, "BERTAHAP": 1, "HINDARI": -1, "LINDUNGI": -1}
MIN_CONFIDENCE = 35
MIN_STABILITY = 60
IDX_LOT = 100


def _check(id_, nama, status, detail, perbaikan=None, bobot=1.0):
    return {"id": id_, "nama": nama, "status": status, "detail": detail, "perbaikan": perbaikan, "bobot": bobot}


def _verdict(checks: List[dict]) -> str:
    if any(c["status"] == GAGAL for c in checks):
        return "diblokir"
    return "lulus dengan catatan" if any(c["status"] == PERINGATAN for c in checks) else "lulus"


# ---------------------------------------------------------------- Gerbang 1

def preflight(kind: str, meta: dict) -> dict:
    """meta: lihat insight/service.preflight_meta. Mengembalikan {checks, verdict, blocking}."""
    c = []
    age, interval = meta.get("umur_data_detik"), meta.get("interval", 60)
    if age is None:
        c.append(_check("kesegaran", "Kesegaran data pasar", GAGAL, "Data pasar belum pernah dimuat",
                        "Tunggu siklus data pertama (±1 menit) atau periksa /api/health/market-data"))
    elif age > 6 * 3600 and meta.get("error_terakhir"):
        c.append(_check("kesegaran", "Kesegaran data pasar", GAGAL,
                        f"Data terakhir {age / 3600:.1f} jam lalu, sumber sedang error: {meta['error_terakhir']}",
                        "Periksa koneksi ke Yahoo/CoinGecko di /api/health/market-data"))
    elif age > 3 * interval:
        c.append(_check("kesegaran", "Kesegaran data pasar", PERINGATAN, f"Data terakhir {age / 60:.0f} menit lalu",
                        "Keputusan memakai harga yang mungkin sudah bergerak"))
    else:
        c.append(_check("kesegaran", "Kesegaran data pasar", LULUS, f"Diperbarui {age:.0f} detik lalu"))

    if kind == "peluang":
        price, candles = meta.get("harga"), meta.get("candle") or 0
        if price is None or not math.isfinite(price) or price <= 0:
            c.append(_check("harga", "Harga valid", GAGAL, f"Harga tidak valid: {price}", "Tunggu data simbol ini termuat"))
        else:
            c.append(_check("harga", "Harga valid", LULUS, f"Harga {price:.6g}"))
        if candles < 60:
            c.append(_check("candle", "Riwayat candle", GAGAL, f"Hanya {candles} candle (butuh ≥ 60 untuk indikator)",
                            "Pilih simbol dengan riwayat lebih panjang"))
        elif candles < 200:
            c.append(_check("candle", "Riwayat candle", PERINGATAN, f"{candles} candle: tren MA200 belum bisa dinilai"))
        else:
            c.append(_check("candle", "Riwayat candle", LULUS, f"{candles} candle harian"))
        if meta.get("high_low_terbalik"):
            c.append(_check("anomali", "Anomali data", GAGAL, "Ada candle dengan high < low (data rusak)",
                            "Tunggu pembaruan data berikutnya"))
        elif (meta.get("lonjakan_maks_persen") or 0) > 25:
            c.append(_check("anomali", "Anomali data", PERINGATAN,
                            f"Lonjakan {meta['lonjakan_maks_persen']:.1f}% antar hari dalam 5 hari terakhir",
                            "Cek aksi korporasi (split/right issue) sebelum memakai sinyal teknikal"))
        else:
            c.append(_check("anomali", "Anomali data", LULUS, "Tidak ada lonjakan/kerusakan candle"))
        n = meta.get("analog_n")
        c.append(_check("analog", "Pengalaman analog historis", LULUS if n else PERINGATAN,
                        f"{n} kejadian serupa" if n else "Tidak cukup kejadian serupa (< 30)",
                        None if n else "Keputusan bertumpu pada bukti lain; perlakukan dengan hati-hati"))
        news = meta.get("berita")
        c.append(_check("berita", "Sumber berita", LULUS if news else PERINGATAN,
                        f"{news} berita terbaru" if news else "Tidak ada berita untuk simbol ini",
                        None if news else "Sentimen berita tidak ikut dinilai", bobot=0.5))

    if kind == "strategi":
        n = meta.get("strategi_tertutup") or 0
        c.append(_check("kinerja_strategi", "Bukti kinerja strategi", LULUS if n >= 20 else PERINGATAN,
                        f"{n} sinyal tertutup", None if n >= 20 else "Kesimpulan tentang strategi ini masih prematur"))

    exp = meta.get("pengalaman") or 0
    c.append(_check("pengalaman", "Pengalaman sinyal tertutup", LULUS if exp >= 20 else PERINGATAN,
                    f"{exp} sinyal tertutup", None if exp >= 20 else "Pola berhasil/gagal belum bisa ditambang", bobot=0.5))
    acc = meta.get("akurasi_ml")
    c.append(_check("model_ml", "Model ML teruji", LULUS if acc and acc >= 0.52 else PERINGATAN,
                    f"Akurasi uji {acc:.1%}" if acc else "Model belum dilatih",
                    None if acc and acc >= 0.52 else "Sinyal ML tidak ikut menjadi bukti", bobot=0.5))
    v = _verdict(c)
    return {"checks": c, "verdict": v, "blocking": v == "diblokir"}


# ---------------------------------------------------------------- Gerbang 2

def position_size(price: float, sl: Optional[float], fx: Optional[float], capital: float, cash: float,
                  risk_per_trade: float, idx: bool) -> Optional[dict]:
    """Ukuran maksimum agar rugi saat kena SL ≤ risk_per_trade × modal; dibatasi kas; lot IDX 100 lembar."""
    if not sl or not fx or sl >= price:
        return None
    risk_unit = (price - sl) * fx
    qty = capital * risk_per_trade / risk_unit
    by_cash = cash / (price * fx) if price * fx > 0 else 0
    limited = by_cash < qty
    qty = min(qty, by_cash)
    if idx:
        qty = math.floor(qty / IDX_LOT) * IDX_LOT
    else:
        qty = math.floor(qty * 1e6) / 1e6
    return {"jumlah_maks": qty, "risiko_idr": round(qty * risk_unit), "nilai_idr": round(qty * price * fx),
            "dibatasi_kas": limited, "risiko_per_trade": risk_per_trade}


def robustness(fw: dict, rebuild: Callable[[frozenset], dict]) -> Tuple[Optional[float], List[str]]:
    """Ablation: buang satu bukti setiap kali; % rekomendasi tetap sama + bukti yang membaliknya."""
    ev = fw["hipotesis"]["bukti"]
    if len(ev) < 2:
        return None, []
    base = fw["keputusan"]["rekomendasi"]["operator"]
    flippers = [e["teks"] for e in ev if rebuild(frozenset({e["teks"]}))["keputusan"]["rekomendasi"]["operator"] != base]
    return round((len(ev) - len(flippers)) / len(ev) * 100), flippers


def review(fw: dict, rebuild: Callable[[frozenset], dict], operator_stats: Dict[str, Tuple[int, int]],
           capital: float, cash: float, risk_per_trade: float, fx: Optional[float], pre_checks=()) -> dict:
    """pre_checks: cek preflight; peringatannya ikut mengurangi keyakinan (satu skor untuk kedua gerbang)."""
    rec = fw["keputusan"]["rekomendasi"]
    alts = fw["alternatif"]
    summ = fw["hipotesis"]["ringkasan"]
    facts = fw["fakta"]
    c = []

    d = DIRECTION.get(rec["operator"], 0)
    if summ and d == 1 and summ["bias"] == "bearish":
        c.append(_check("arah", "Konsistensi arah", GAGAL, "Rekomendasi membeli padahal bukti condong turun"))
    elif summ and d == -1 and summ["bias"] == "bullish" and summ["net"] > 2:
        c.append(_check("arah", "Konsistensi arah", PERINGATAN, "Rekomendasi menghindar padahal bukti kuat condong naik"))
    else:
        c.append(_check("arah", "Konsistensi arah", LULUS, "Arah rekomendasi selaras dengan bukti"))

    act = rec.get("aksi") or {}
    if act.get("tipe") == "buy":
        price = facts.get("harga")
        if not act.get("stop_loss"):
            c.append(_check("level", "Level SL/TP wajar", PERINGATAN, "Aksi beli tanpa stop loss: risiko tidak terbatas",
                            "Tentukan stop loss sebelum eksekusi"))
        elif not valid_levels(True, price, act["stop_loss"], act.get("take_profit")):
            c.append(_check("level", "Level SL/TP wajar", GAGAL, f"Level tidak konsisten (SL {act['stop_loss']}, "
                                                                  f"harga {price}, TP {act.get('take_profit')})"))
        else:
            c.append(_check("level", "Level SL/TP wajar", LULUS, "SL < harga < TP"))

    gap = alts[0]["skor"] - alts[1]["skor"]
    if alts[0]["skor"] < 40:
        c.append(_check("kekuatan", "Kekuatan rekomendasi", PERINGATAN, f"Skor tertinggi hanya {alts[0]['skor']}",
                        "Tidak ada alternatif yang kuat; menunggu/riset lebih aman"))
    elif gap < 5:
        c.append(_check("kekuatan", "Kekuatan rekomendasi", PERINGATAN,
                        f"Keputusan tipis: selisih #1 dan #2 hanya {gap} poin ({alts[1]['judul']})"))
    else:
        c.append(_check("kekuatan", "Kekuatan rekomendasi", LULUS, f"Unggul {gap} poin dari alternatif berikutnya"))

    if summ:
        c.append(_check("kecukupan_bukti", "Jumlah bukti", LULUS if summ["jumlah_bukti"] >= 3 else PERINGATAN,
                        f"{summ['jumlah_bukti']} bukti"))
        c.append(_check("konflik", "Kesepakatan bukti", LULUS if summ["kesepakatan_bukti"] >= 30 else PERINGATAN,
                        f"Kesepakatan {summ['kesepakatan_bukti']}%",
                        None if summ["kesepakatan_bukti"] >= 30 else "Bukti saling bertentangan"))

    stability, flippers = robustness(fw, rebuild)
    if stability is not None:
        c.append(_check("ketahanan", "Uji ketahanan (ablation)", LULUS if stability >= MIN_STABILITY else PERINGATAN,
                        f"Rekomendasi bertahan di {stability}% uji tanpa satu bukti"
                        + (f"; dibalik oleh: {'; '.join(flippers[:3])}" if flippers else ""),
                        None if stability >= MIN_STABILITY else "Keputusan bergantung pada sedikit bukti — rapuh"))

    s, f = operator_stats.get(rec["operator"], (0, 0))
    if s + f >= 10:
        hit = s / (s + f) * 100
        c.append(_check("kalibrasi", "Rekam jejak pola pikir", LULUS if hit >= 40 else PERINGATAN,
                        f"{rec['operator']} berhasil {hit:.0f}% dari {s + f} keputusan"))

    size = None
    if act.get("tipe") == "buy":
        sym = facts.get("simbol", "")
        size = position_size(facts.get("harga"), act.get("stop_loss"), fx, capital, cash, risk_per_trade, sym.endswith(".JK"))
        if size is not None:
            c.append(_check("risiko", "Kontrol ukuran posisi", PERINGATAN if size["dibatasi_kas"] or size["jumlah_maks"] <= 0 else LULUS,
                            f"Maksimal {size['jumlah_maks']:g} unit (rugi maks ± {size['risiko_idr']:,} IDR saat kena SL)"
                            + (" — dibatasi kas" if size["dibatasi_kas"] else "")))

    # advokat setan: argumen terkuat MELAWAN rekomendasi
    ev = fw["hipotesis"]["bukti"]
    # d=0 (TUNDA/RISET/GANTI): lawan "menunggu" adalah bukti terkuat ke arah mana pun yang menuntut tindakan sekarang
    against = sorted((e for e in ev if (e["bobot"] < 0 if d > 0 else e["bobot"] > 0 if d < 0 else e["bobot"] != 0)),
                     key=lambda e: -abs(e["bobot"]))
    devil = [e["teks"] for e in against[:3]] + [
        f"Pola gagal: {' & '.join(f'{k}={v}' for k, v in p['kondisi'].items())} (WR {p['win_rate']}%)"
        for p in fw["pengalaman"].get("pola", {}).get("gagal", [])[:1]]

    score = 100.0
    for x in [*c, *pre_checks]:
        score -= {PERINGATAN: 8 * x["bobot"], GAGAL: 35}.get(x["status"], 0)
    if stability is not None:
        score *= 0.5 + 0.5 * stability / 100
    confidence = max(0, min(100, round(score)))

    final = dict(rec)
    failed = [x for x in c if x["status"] == GAGAL]
    if failed or confidence < MIN_CONFIDENCE:
        safe = max((a for a in alts if a["operator"] in ("TUNDA", "RISET")), key=lambda a: a["skor"])
        final = dict(safe)
        final["alasan_kontrol"] = ("; ".join(x["detail"] for x in failed) if failed
                                   else f"keyakinan {confidence} di bawah ambang {MIN_CONFIDENCE}")
    return {"checks": c, "verdict": _verdict(c), "keyakinan": confidence, "stabilitas": stability,
            "pembalik": flippers, "advokat_setan": devil or ["Tidak ada bukti kontra yang tercatat"],
            "ukuran_posisi": size, "keputusan_final": final,
            "diturunkan": final["operator"] != rec["operator"]}
