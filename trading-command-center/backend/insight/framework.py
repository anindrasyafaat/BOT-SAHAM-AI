"""
Generator kerangka berpikir.

Alur tetap untuk setiap kasus:
  1. Masalah     -> apa yang sebenarnya diputuskan
  2. Fakta       -> data sekarang (tanpa opini)
  3. Pengalaman  -> pola dari sinyal tertutup + analog historis kondisi serupa
  4. Hipotesis   -> bukti pro & kontra, masing-masing berbobot
  5. Alternatif  -> dibangkitkan oleh operator pola pikir (bukan satu jawaban), lalu dinilai bukti
  6. Keputusan   -> peringkat, checklist, pre-mortem ("kalau gagal, kenapa?")
  7. Belajar     -> apa yang dicatat agar keputusan berikutnya lebih baik

Fungsi di sini murni (tanpa I/O) agar mudah diuji; data dikumpulkan oleh insight/service.py.
"""

from typing import Dict, List, Optional, Tuple

# Operator pola pikir: cara sistematis membangkitkan alternatif dari satu masalah.
OPERATORS = {
    "LAKUKAN": "Eksekusi sekarang",
    "BERTAHAP": "Ubah ukuran: masuk/keluar bertahap",
    "TUNDA": "Tunda sampai ada konfirmasi",
    "GANTI": "Ganti pendekatan ke pola yang terbukti",
    "LINDUNGI": "Lindungi risiko lebih dulu",
    "HINDARI": "Hindari / balik arah",
    "RISET": "Kumpulkan bukti tambahan",
}
KINDS = ("peluang", "strategi", "portofolio", "bebas")


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def operator_prior(stats: Dict[str, Tuple[int, int]], op: str) -> Tuple[float, float]:
    """Posterior Beta(1,1) dari hasil pilihan operator sebelumnya -> (rata-rata %, bobot 0..0.5)."""
    s, f = stats.get(op, (0, 0))
    n = s + f
    return (s + 1) / (n + 2) * 100, min(0.5, n / (n + 10))


def _blend(base: float, op: str, stats) -> Tuple[float, Optional[float]]:
    mean, w = operator_prior(stats, op)
    return _clamp(base * (1 - w) + mean * w), (round(mean, 1) if w > 0 else None)


# ---------------------------------------------------------------- bukti

def evidence_for_symbol(facts: dict, experience: dict) -> List[dict]:
    """Daftar bukti berbobot (+ = mendukung naik, - = mendukung turun)."""
    ev = []
    ctx = facts.get("konteks", {})
    add = lambda w, teks, sumber: ev.append({"bobot": round(w, 2), "teks": teks, "sumber": sumber})

    a = experience.get("analog")
    if a:
        w = (a["peluang_naik"] - 50) / 10
        add(w, f"Kondisi serupa ({a['n']} kejadian, {a['simbol']} simbol): naik {a['peluang_naik']}% dalam "
               f"{a['horizon_hari']} hari, median {a['median_return']}%", "analog historis")
    reg = ctx.get("regime")
    if reg == "naik":
        add(1.0, "Tren naik: harga > MA50 > MA200", "tren")
    elif reg == "turun":
        add(-1.0, "Tren turun: harga < MA50 < MA200", "tren")
    rsi = ctx.get("rsi")
    if rsi == "overbought":
        add(-0.5, f"RSI {ctx.get('rsi_value')} overbought: rawan koreksi", "momentum")
    elif rsi == "oversold":
        add(0.5 if reg != "turun" else 0.0, f"RSI {ctx.get('rsi_value')} oversold" +
            (": peluang pantul" if reg != "turun" else ", tetapi dalam tren turun (pisau jatuh)"), "momentum")
    if ctx.get("volume") == "tinggi":
        chg = facts.get("perubahan_persen") or 0
        add(0.5 if chg > 0 else -0.5, f"Volume tinggi mengonfirmasi gerak {chg:+.2f}%", "volume")
    s = facts.get("sentimen_berita")
    if s is not None and abs(s) > 0.1:
        add(max(-1.0, min(1.0, s * 2)), f"Sentimen berita {s:+.2f}", "berita")
    for sig in facts.get("sinyal_aktif", []):
        buy = "BUY" in sig["arah"]
        add((0.5 if buy else -0.5) * sig["confidence"] / 100,
            f"Sinyal {sig['arah']} {sig['strategi']} ({sig['confidence']:.0f}%)", "sinyal")
    for p in experience.get("pola", {}).get("berhasil", [])[:3]:
        add(min(1.5, (p["wilson_bawah"] - 40) / 20), f"Pola berhasil {_fmt_kondisi(p)}: WR {p['win_rate']}% (n={p['n']})", "pola")
    for p in experience.get("pola", {}).get("gagal", [])[:3]:
        add(-min(1.5, (60 - p["wilson_atas"]) / 20), f"Pola gagal {_fmt_kondisi(p)}: WR {p['win_rate']}% (n={p['n']})", "pola")
    return ev


def _fmt_kondisi(p: dict) -> str:
    return " & ".join(f"{k}={v}" for k, v in p["kondisi"].items())


def summarize(ev: List[dict]) -> dict:
    pro = sum(e["bobot"] for e in ev if e["bobot"] > 0)
    kontra = -sum(e["bobot"] for e in ev if e["bobot"] < 0)
    net = pro - kontra
    total = pro + kontra
    agreement = abs(net) / total if total else 0.0
    bias = "bullish" if net > 1 else "bearish" if net < -1 else "netral"
    return {"pro": round(pro, 2), "kontra": round(kontra, 2), "net": round(net, 2), "bias": bias,
            "kesepakatan_bukti": round(agreement * 100), "jumlah_bukti": len(ev)}


# ---------------------------------------------------------------- alternatif per jenis kasus

def _alt(op, judul, alasan, base, stats, risiko, pemicu, batal, aksi=None):
    skor, prior = _blend(base, op, stats)
    return {"operator": op, "pola_pikir": OPERATORS[op], "judul": judul, "alasan": alasan, "skor": round(skor),
            "skor_bukti": round(_clamp(base)), "rekam_jejak_operator": prior, "risiko": risiko,
            "pemicu": pemicu, "titik_batal": batal, "aksi": aksi}


def alternatives_peluang(facts, experience, summ, stats) -> List[dict]:
    net, agree = summ["net"], summ["kesepakatan_bukti"]
    strength = _clamp(50 + net * 12)               # 0..100, 50 = netral
    uncertainty = 100 - agree
    a = experience.get("analog") or {}
    price = facts.get("harga")
    # analog bearish bisa memberi p90 < 0 -> TP di bawah harga; level yang tak masuk akal tidak disarankan
    sl = round(price * (1 + a["p10"] / 100), 4) if price and a and a["p10"] < 0 else None
    tp = round(price * (1 + a["p90"] / 100), 4) if price and a and a["p90"] > 0 else None
    thin = summ["jumlah_bukti"] < 3 or not a  # analog_stats sudah menjamin n >= 30 bila ada
    sym = facts["simbol"]
    best = next((p for p in experience.get("pola", {}).get("berhasil", []) if "strategi" in p["kondisi"]), None)
    holding = facts.get("posisi")
    return [
        _alt("LAKUKAN", f"Beli {sym} sekarang", "Bukti condong naik dan cukup sepakat", strength * agree / 100 * 1.6,
             stats, "Masuk penuh saat bukti salah = kerugian penuh", "Sekarang", f"Tutup bila harga ≤ {sl}" if sl else "Pasang stop loss",
             {"tipe": "buy", "simbol": sym, "stop_loss": sl, "take_profit": tp}),
        _alt("BERTAHAP", f"Beli {sym} 1/3 dulu, tambah saat terkonfirmasi",
             "Condong naik tetapi bukti belum sepakat / volatilitas tinggi", _clamp(strength - 10) * (0.6 + uncertainty / 250),
             stats, "Rata-rata harga beli naik bila terus menguat", "1/3 sekarang; 1/3 di atas high 5 hari; 1/3 setelah koreksi sehat",
             f"Batalkan sisa bila harga ≤ {sl}" if sl else "Batalkan bila tren patah",
             {"tipe": "buy", "simbol": sym, "porsi": 0.33, "stop_loss": sl, "take_profit": tp}),
        _alt("TUNDA", f"Tunggu konfirmasi untuk {sym}", "Bukti bertentangan; menunggu lebih murah daripada menebak",
             uncertainty * 0.8 + (10 if facts.get("konteks", {}).get("rsi") == "overbought" else 0), stats,
             "Ketinggalan sebagian kenaikan", "Close di atas MA20 dengan volume ≥ rata-rata, atau RSI kembali < 70",
             "Bila tren berubah turun, beralih ke HINDARI"),
        _alt("GANTI", f"Pakai pendekatan {best['kondisi']['strategi']}" if best else "Pakai pola yang terbukti",
             f"Pola {_fmt_kondisi(best)} WR {best['win_rate']}% (n={best['n']})" if best else "Belum ada pola terbukti untuk kondisi ini",
             (best["wilson_bawah"] if best else 15), stats, "Pola masa lalu bisa berhenti bekerja",
             "Tunggu sinyal dari strategi tersebut", "Pola turun di bawah 50% pada evaluasi berikutnya"),
        _alt("LINDUNGI", f"Kurangi/lindungi posisi {sym}" if holding else f"Tetapkan batas rugi sebelum menyentuh {sym}",
             "Bukti condong turun" + (" dan Anda memegang posisi" if holding else ""),
             _clamp(50 - net * 12) * (1.2 if holding else 0.6), stats, "Terjual sebelum pantulan",
             "Pasang stop loss di bawah swing low terakhir", "Bila bukti berbalik naik, kembali ke rencana awal",
             {"tipe": "sell", "simbol": sym} if holding else None),
        _alt("HINDARI", f"Jangan masuk {sym} dulu", "Bukti condong turun / pola gagal cocok dengan kondisi sekarang",
             _clamp(50 - net * 12) * agree / 100 * 1.6, stats, "Kehilangan peluang bila analisa keliru",
             "Sekarang", "Masuk lagi ke daftar pantau saat tren berbalik naik"),
        _alt("RISET", f"Kumpulkan bukti tambahan untuk {sym}", "Sampel pengalaman tipis" if thin else "Bukti sudah cukup",
             60 if thin else 15, stats, "Waktu terbuang", "Baca berita & laporan keuangan terbaru; tunggu 20+ sinyal tertutup",
             "-"),
    ]


def alternatives_strategi(facts, experience, stats) -> List[dict]:
    st = facts.get("strategi_stat", {})
    closed, wr, exp = st.get("tertutup", 0), st.get("win_rate") or 0, st.get("expectancy") or 0
    losing = exp < 0
    fails = experience.get("pola", {}).get("gagal", [])
    worst = fails[0] if fails else None
    better = next((p for p in experience.get("pola", {}).get("berhasil", [])
                   if p["kondisi"].get("strategi") not in (None, facts["strategi"])), None)
    name = facts["strategi"]
    small = closed < 20
    return [
        _alt("LAKUKAN", f"Pertahankan {name} apa adanya", "Sampel masih kecil" if small else "Kinerja masih positif",
             70 if (small or not losing) else 10, stats, "Kerugian berlanjut bila memang rusak", "Sekarang",
             "Expectancy negatif setelah 20 sinyal tertutup"),
        _alt("TUNDA", f"Naikkan ambang confidence {name}", "Hanya ambil sinyal paling yakin",
             55 if losing else 25, stats, "Sinyal jadi jarang", "Ambang +5", "Win rate tidak membaik setelah 10 sinyal"),
        _alt("LINDUNGI", f"Filter: jangan jalankan {name} saat {_fmt_kondisi(worst)}" if worst else f"Tambah filter konteks untuk {name}",
             f"Pola gagal: WR {worst['win_rate']}% (n={worst['n']})" if worst else "Belum ada pola gagal yang signifikan",
             (100 - worst["wilson_atas"]) if worst else 20, stats, "Filter terlalu ketat", "Terapkan filter pada sinyal berikutnya",
             "Kondisi tersebut berubah menjadi menguntungkan"),
        _alt("GANTI", f"Alihkan bobot ke {better['kondisi']['strategi']}" if better else "Alihkan ke strategi lain yang terbukti",
             f"Pola {_fmt_kondisi(better)} WR {better['win_rate']}%" if better else "Belum ada pembanding yang terbukti",
             (better["wilson_bawah"] if better else 10), stats, "Strategi pengganti juga bisa menurun", "Bandingkan 20 sinyal berikutnya",
             "Pengganti tidak lebih baik"),
        _alt("BERTAHAP", f"Kecilkan ukuran posisi dari sinyal {name} 50%", "Kurangi dampak sambil tetap mengumpulkan data",
             45 if losing else 20, stats, "Untung juga ikut mengecil", "Sekarang", "Expectancy kembali positif"),
        _alt("HINDARI", f"Matikan {name} sementara", f"Win rate {wr:.0f}%, expectancy {exp:.2f}%",
             (80 if (losing and not small and wr < 40) else 30 if losing else 5), stats, "Melewatkan pemulihan strategi",
             "Toggle di halaman AI Brain", "Aktifkan lagi setelah uji ulang", {"tipe": "toggle_strategy", "strategi": name}),
        _alt("RISET", f"Uji ulang {name} di data 1 tahun", "Pastikan masalahnya di strategi, bukan kebetulan",
             60 if small else 35, stats, "Butuh waktu", "Bandingkan per regime pasar", "-"),
    ]


def alternatives_portofolio(facts, stats) -> List[dict]:
    p = facts.get("portofolio", {})
    dd = p.get("drawdown_persen", 0)
    conc = p.get("konsentrasi_terbesar_persen", 0)
    no_sl = p.get("posisi_tanpa_sl", 0)
    losers = p.get("posisi_rugi", 0)
    stressed = dd < -5 or losers > 0
    empty = not p.get("jumlah_posisi")
    return [
        _alt("LAKUKAN", "Tetap kas sampai ada peluang berbukti kuat" if empty else "Tahan semua posisi sesuai rencana",
             "Belum ada posisi; masuk hanya lewat kasus peluang dengan rekomendasi LAKUKAN/BERTAHAP" if empty
             else "Risiko masih dalam batas", 60 if not stressed else 20, stats,
             "Ketinggalan pasar" if empty else "Rugi membesar bila pasar terus turun", "Sekarang",
             "Ada kasus peluang dengan skor LAKUKAN ≥ 60" if empty else "Drawdown melewati -10%"),
        _alt("LINDUNGI", f"Pasang stop loss pada {no_sl} posisi tanpa SL", "Posisi tanpa batas rugi adalah risiko terbuka",
             90 if no_sl else 10, stats, "Kena stop sebelum pantulan", "Sekarang", "-"),
        _alt("BERTAHAP", f"Kurangi posisi terbesar ({conc:.0f}% portofolio) ke ≤ 25%", "Konsentrasi membuat satu kesalahan jadi besar",
             _clamp((conc - 25) * 2), stats, "Upside berkurang", "Jual bertahap 2 kali", "-"),
        _alt("HINDARI", "Jeda pembelian baru sampai drawdown pulih", f"Drawdown {dd:.1f}%", _clamp(-dd * 6), stats,
             "Melewatkan peluang", "Sekarang", "Drawdown kembali di atas -3%"),
        _alt("GANTI", "Rotasi dari posisi rugi ke aset dengan analog terbaik", "Modal dipindah ke kondisi yang secara historis lebih baik",
             35 if losers else 10, stats, "Merealisasikan rugi", "Bandingkan analog posisi rugi vs kandidat", "-"),
        _alt("TUNDA", "Evaluasi ulang setelah 5 hari perdagangan", "Hindari keputusan emosional", 40, stats,
             "Kondisi memburuk selama menunggu", "Tanggal evaluasi", "Drawdown melewati -10%"),
        _alt("RISET", "Investigasi akar masalah kerugian", "Bedakan rugi karena proses vs karena probabilitas",
             50 if stressed else 15, stats, "Waktu", "Pakai skill investigasi-kerugian", "-"),
    ]


# ---------------------------------------------------------------- perakitan kerangka

def build(kind: str, facts: dict, experience: dict, operator_stats: Dict[str, Tuple[int, int]], masalah: str) -> dict:
    if kind not in KINDS:
        raise ValueError(f"jenis kasus harus salah satu dari {KINDS}")
    ev, summ = [], None
    if kind in ("peluang", "bebas") and facts.get("simbol"):
        ev = evidence_for_symbol(facts, experience)
        summ = summarize(ev)
        alts = alternatives_peluang(facts, experience, summ, operator_stats)
    elif kind == "strategi":
        alts = alternatives_strategi(facts, experience, operator_stats)
    else:
        alts = alternatives_portofolio(facts, operator_stats)
    alts.sort(key=lambda a: -a["skor"])
    pre_mortem = [e["teks"] for e in sorted(ev, key=lambda e: e["bobot"])[:3] if e["bobot"] < 0] if summ and summ["bias"] != "bearish" \
        else [e["teks"] for e in sorted(ev, key=lambda e: -e["bobot"])[:3] if e["bobot"] > 0]
    pre_mortem += [f"Pola gagal serupa: {_fmt_kondisi(p)}" for p in experience.get("pola", {}).get("gagal", [])[:2]]
    return {
        "jenis": kind,
        "masalah": masalah,
        "fakta": facts,
        "pengalaman": experience,
        "hipotesis": {"bukti": sorted(ev, key=lambda e: -abs(e["bobot"])), "ringkasan": summ},
        "alternatif": alts,
        "keputusan": {
            "rekomendasi": alts[0],
            "cadangan": alts[1],
            "checklist": [
                "Tren searah dengan rencana?", "Ada konfirmasi volume?", "Berita terbaru tidak bertentangan?",
                "Risk:reward ≥ 1.5?", "Ukuran posisi ≤ risiko per trade?", "Stop loss sudah ditentukan sebelum masuk?",
            ],
            "pre_mortem": pre_mortem or ["Belum ada bukti kontra yang kuat — waspadai kejadian tak terduga (berita, gap)"],
        },
        "rencana_belajar": [
            "Pilih satu alternatif agar sistem tahu keputusan Anda",
            "Hasil kasus peluang dinilai otomatis setelah 5 hari perdagangan; kasus lain tandai manual",
            "Setiap hasil memperbarui rekam jejak operator pola pikir untuk keputusan berikutnya",
        ],
    }


def narrative(fw: dict) -> str:
    """Ringkasan template (dipakai bila LLM lokal tidak aktif atau ditolak penjaga halusinasi)."""
    rec, alt2 = fw["keputusan"]["rekomendasi"], fw["keputusan"]["cadangan"]
    s = fw["hipotesis"]["ringkasan"]
    head = (f"Bukti condong {s['bias']} (pro {s['pro']}, kontra {s['kontra']}, kesepakatan {s['kesepakatan_bukti']}%). "
            if s else "")
    return (f"{head}Rekomendasi: {rec['judul']} — {rec['alasan']} (skor {rec['skor']}). "
            f"Cadangan: {alt2['judul']} (skor {alt2['skor']}). Batal bila: {rec['titik_batal']}.")
