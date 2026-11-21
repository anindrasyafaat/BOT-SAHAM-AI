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
```

## Jujur soal angka "90%"
Penghematan 85–90% bisa dicapai untuk **token input** di sesi panjang, karena hampir semua konteks dibaca dari cache. Total biaya berbobot (termasuk output dan penulisan cache) biasanya hemat 70–85%. Angka pastinya tergantung pola kerja, jadi ukur dengan `audit-token`, jangan cuma percaya klaim.
