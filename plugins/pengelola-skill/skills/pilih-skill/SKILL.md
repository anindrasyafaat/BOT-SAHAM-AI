---
name: pilih-skill
description: "Manajer skill yang belajar sendiri: menentukan skill mana yang paling cocok dan paling kuat untuk sebuah pekerjaan (dengan memperhitungkan pengalaman berhasil/gagal sebelumnya), mencarikan rekomendasi skill terbaik di GitHub berdasarkan jumlah bintang bila belum ada, dan mengusulkan skill baru dari kebutuhan yang berulang. Gunakan saat pengguna berkata \"skill apa yang cocok\", \"pakai skill apa\", \"pilihkan skill\", \"rekomendasi skill\", \"cari skill di github\", \"ada skill untuk ...?\", \"dashboard skill\", \"evolusi skill\", atau sebelum mengerjakan tugas besar yang belum jelas skill-nya."
---

# Pilih Skill

Tujuan: untuk satu pekerjaan, pilih skill terbaik yang **sudah terpasang**; bila tidak ada yang cocok, beri rekomendasi repo skill dari GitHub yang diurutkan berdasarkan **bintang**.

Skrip: `${CLAUDE_PLUGIN_ROOT}/skills/pilih-skill/scripts/cari_skill.py` (hanya pustaka standar Python 3).

## Langkah

1. **Pahami pekerjaan.** Ringkas jadi satu kalimat tujuan + 3–6 kata kunci. Siapkan kata kunci **Indonesia dan Inggris** (deskripsi skill campuran dua bahasa), mis. `analisa saham teknikal stock technical analysis`.

2. **Cek skill terpasang**, dua sumber:
   - Daftar skill yang tersedia di sesi ini (daftar skill di konteks Anda). Ini sumber utama: ia juga memuat skill bawaan yang tidak ada di disk.
   - Pemindaian disk (`~/.claude/skills`, `~/.claude/plugins`, `.claude/skills`):
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/skills/pilih-skill/scripts/cari_skill.py" lokal "<kata kunci ID + EN>"
     ```
     Skor 0–1 = porsi kata kunci yang cocok (nama skill bernilai ganda). Ini penyaring kasar, bukan keputusan akhir.

3. **Nilai kecocokan dan kekuatan** setiap kandidat dengan membaca deskripsinya (buka `SKILL.md`-nya bila ragu):
   - **Cocok**: deskripsi menyebut pekerjaan ini atau pemicu yang mirip, bukan sekadar kata yang sama.
   - **Kuat**: punya skrip/referensi sendiri, cakupan langkah lengkap, spesifik untuk domain, terhubung ke data/alat nyata. Skill orkestrator (mis. `god-mode`) menang bila pekerjaan butuh beberapa skill sekaligus.
   - Skill **proses** (brainstorming, debugging, TDD) bisa dipakai bersama skill domain; sebutkan urutannya.

4. **Jika ada yang cocok** → keluarkan tabel lalu langsung pakai skill teratas (panggil lewat tool Skill) kecuali pengguna hanya meminta rekomendasi.

   | # | Skill | Kenapa cocok | Kekuatan | Cara pakai |
   |---|-------|--------------|----------|------------|

5. **Jika tidak ada yang cocok** (skor rendah dan deskripsi tidak relevan) → cari di GitHub dengan kata kunci **Inggris** 2–4 kata:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/pilih-skill/scripts/cari_skill.py" github "<english keywords>" --top 10
   ```
   Skrip mencoba berurutan `topic:claude-skills`, `topic:agent-skills`, `"<kw> claude skill"`, `"<kw> skill"`, lalu `<kw>`, menggabungkan hasil, dan mengurutkan berdasarkan bintang. Jika hasil kosong, ulangi dengan kata kunci lebih umum. Jika kena batas rate, sarankan set `GITHUB_TOKEN`.

   Sajikan 3–5 teratas:

   | # | Repo | ★ | Update terakhir | Isi singkat | Cara pasang |
   |---|------|---|-----------------|-------------|-------------|

   Cara pasang yang umum:
   - Repo berisi `.claude-plugin/marketplace.json` → `/plugin marketplace add <owner>/<repo>` lalu `/plugin install <nama>@<marketplace>`.
   - Repo berisi folder skill (`SKILL.md`) → salin folder itu ke `~/.claude/skills/<nama>/`.
   Periksa struktur repo dulu (README / daftar file) sebelum menyebut cara pasang.

6. **Peringatan wajib** saat merekomendasikan repo GitHub: bintang ≠ aman. Sarankan membaca `SKILL.md` dan skrip di dalamnya sebelum memasang, utamakan repo yang aktif (update < 6 bulan) dan berlisensi jelas. Jangan memasang apa pun tanpa persetujuan pengguna.

7. **Belajar dari hasil (wajib setelah skill dipakai).** Setelah pekerjaan selesai, nilai jujur apakah skill pilihan benar-benar membantu, lalu catat:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/pilih-skill/scripts/cari_skill.py" catat <plugin:skill> "<tugas>" --hasil berhasil|gagal --catatan "<alasan singkat>"
   ```
   Catatan ini menggeser peringkat berikutnya untuk tugas mirip (maks ±0.3): skill yang terbukti naik, yang gagal turun. Skill bawaan yang tidak ada di disk tetap muncul lewat baris `[pengalaman +x]`. Pemindaian `lokal` yang tidak menemukan apa pun otomatis dicatat sebagai **celah**.

8. **Evolusi (kembangkan kemampuan sendiri).** Jalankan saat memulai sesi besar, atau bila pengguna meminta:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/pilih-skill/scripts/cari_skill.py" evolusi
   ```
   - `USULAN_SKILL_BARU` = kebutuhan yang ≥2 kali muncul tanpa skill. Tawarkan ke pengguna: cari dulu di GitHub (langkah 5); jika tidak ada yang layak, buat skill baru di `~/.claude/skills/<nama>/SKILL.md` dengan skill `skill-creator` (bila tersedia) dari pengetahuan yang terbukti berhasil di sesi ini. Setelah dibuat, `catat` pemakaian pertamanya agar celah tertutup.
   - `SKILL_LEMAH` = skill yang lebih sering gagal. Usulkan pengganti atau perbaikan.
   Jangan membuat atau memasang skill tanpa persetujuan pengguna.

9. **Dashboard.** Untuk gambaran lengkap (katalog, uji pekerjaan interaktif, papan pengalaman, usulan evolusi, cache rekomendasi GitHub):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/pilih-skill/scripts/cari_skill.py" dashboard
   ```
   Hasilnya `~/.claude/pengelola-skill/dashboard.html`; buka di browser atau kirim ke pengguna.

## Catatan

- Jangan mengarang skill atau repo: hanya sebut yang muncul di daftar sesi, hasil `lokal`, atau hasil `github`.
- Bila bintang hampir sama, utamakan yang lebih relevan dan lebih baru diperbarui.
