# hemat-token — plugin Claude Code untuk menghemat token

## Pasang
```
/plugin marketplace add anindrasyafaat/BOT-SAHAM-AI
/plugin install hemat-token@bot-saham-ai
```
Matikan sementara: `HEMAT_TOKEN=off`. Batas baris Read: `HEMAT_TOKEN_MAX_LINES` (bawaan 400).

## Kerangka berpikir
Biaya token ada di tiga tempat. Yang terbesar diserang lebih dulu:

| Sumber biaya | Porsi biasanya | Cara menekan | Bagian plugin |
|---|---|---|---|
| Konteks yang dikirim ulang setiap giliran | 60–90% | prompt cache (dibaca hanya 0,1x harga) + konteks tetap kecil | `rules.md` (aturan tetap, jadi cache terus kena) |
| Hasil tool (isi file, log) | tetap ada di konteks sampai sesi selesai | grep dulu, baca hanya rentang yang perlu, potong output | `hooks/read-guard.js` |
| Output | 10–30% (5x harga input) | jawaban langsung, diff bukan file penuh | `rules.md` |

**Kualitas tidak dikorbankan.** Setiap tugas wajib melewati *quality gate* sebelum dinyatakan selesai: semua permintaan sudah dikerjakan, ada bukti (test, build, atau screenshot) yang sudah dijalankan dan dibaca hasilnya, dampak ke pemanggil/config/test sudah dicek, dan hal yang dilewati disebutkan terus terang. Jawaban murah yang salah justru menghabiskan lebih banyak token untuk memperbaikinya.

## Isi plugin
- **SessionStart hook** menyuntikkan `rules.md`: aturan singkat soal input, output, dan quality gate.
- **PreToolUse hook (Read)** menolak pembacaan satu file utuh di atas 400 baris dan mengarahkan Claude untuk grep, lalu Read dengan offset/limit. Read sebagian selalu diizinkan, jadi Claude tidak pernah terkunci.
- **Skill `hemat-token`** berisi metode kerja lengkap: rencana, eksekusi, quality gate, dan pengukuran.
- **Skill `audit-token`** + `scripts/token-audit.js` membaca transkrip sesi lalu melaporkan cache hit rate, biaya berbobot dibanding tanpa cache, % penghematan (nilai A ≥ 85%), hasil tool terbesar, dan apa yang perlu diperbaiki.

## Audit dan QC
```
node plugins/hemat-token/test/run.js           # self-check hook + audit
node plugins/hemat-token/scripts/token-audit.js # audit sesi terbaru
node plugins/hemat-token/scripts/token-audit.js --html audit.html   # + laporan HTML
```
Laporan HTML berupa satu file mandiri yang bisa dibuka offline, mendukung mode terang/gelap dan layar ponsel. Isinya: ringkasan penghematan + nilai, komposisi biaya aktual vs tanpa cache, konteks per panggilan API (untuk melihat konteks yang membengkak), 10 hasil tool terbesar beserta nama tool/file-nya, dan daftar perbaikan. Setiap grafik punya tooltip dan tampilan tabel.

## Hasil uji A/B (headless Claude, 21 November 2026)
Tugas: perbaiki bug off-by-one yang ditanam di file 8.400 baris (total 19.000 baris), lalu jalankan test. Setiap arm dijalankan 2x di fixture baru.

| Arm | Test | Biaya run 1 / run 2 | Rata-rata | vs baseline |
|---|---|---|---|---|
| A: tanpa plugin | PASS, PASS | $0,370 / $0,355 | $0,363 | — |
| B: + hemat-token | PASS, PASS | $0,324 / $0,325 | $0,325 | −10% |
| C: + hemat-token + tanpa MCP/skill lain | PASS, PASS | $0,467 (cache dingin) / $0,188 (cache hangat) | — | −48% saat cache hangat |

Temuan:
- Kualitas tetap terjaga: semua 6 run lolos test.
- Sekitar 33 ribu token "overhead tetap" (system prompt, tool, plugin lain) dibaca ulang **setiap giliran**. Ini sumber biaya terbesar, bukan file yang dibaca.
- Penjaga Read tidak terpicu di tugas ini karena model sudah memakai grep + baca sebagian. Penjaga ini menyelamatkan kasus terburuk (baca file besar utuh), bukan kasus rata-rata.
- Ulangi uji: `bench/run-arm.sh A` vs `bench/run-arm.sh B --plugin-dir plugins/hemat-token`, lalu `node bench/summ.js bench/A bench/B`. Ini memakai kuota API sungguhan.

## Jujur soal angka "90%" dan "95%"
Cache dibaca dengan harga 0,1x, jadi penghematan maksimum dari caching adalah **90% untuk input**. Output tidak bisa di-cache. Akibatnya "hemat 95% dari biaya total" tidak mungkin dicapai lewat plugin mana pun dibanding baseline yang sudah memakai cache (Claude Code selalu memakai cache). Angka 95% hanya muncul kalau dibandingkan dengan pola boros, misalnya membaca file besar utuh: diukur di fixture ini, Read 2.000 baris ≈ 10.900 token vs grep + 16 baris ≈ 130 token (hemat 99% untuk langkah itu).

Penghematan 85–90% bisa dicapai untuk **token input** di sesi panjang, karena hampir semua konteks dibaca dari cache. Total biaya berbobot (termasuk output dan penulisan cache) biasanya hemat 70–85%. Angka pastinya tergantung pola kerja, jadi ukur dengan `audit-token`, jangan cuma percaya klaim.
