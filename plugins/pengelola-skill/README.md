# pengelola-skill

Plugin Claude Code untuk memilih skill yang paling cocok dan kuat untuk sebuah pekerjaan. Jika belum ada skill terpasang yang cocok, plugin mencari repo skill di GitHub dan mengurutkannya berdasarkan bintang.

## Pasang

```
/plugin marketplace add anindrasyafaat/BOT-SAHAM-AI
/plugin install pengelola-skill@bot-saham-ai
```

## Pakai

```
/pengelola-skill:pilih-skill analisa teknikal saham BBCA
```

atau cukup tanya: "skill apa yang cocok untuk ...?"

Skrip bisa dijalankan langsung:

```bash
python3 skills/pilih-skill/scripts/cari_skill.py lokal  "analisa saham stock analysis"
python3 skills/pilih-skill/scripts/cari_skill.py github "stock technical analysis" --top 10
```

## Belajar & berevolusi

```bash
python3 skills/pilih-skill/scripts/cari_skill.py catat god-mode-trading:analisa-chart "analisa saham BBCA" --hasil berhasil
python3 skills/pilih-skill/scripts/cari_skill.py evolusi     # celah berulang -> usulan skill baru, skill lemah
python3 skills/pilih-skill/scripts/cari_skill.py dashboard   # ~/.claude/pengelola-skill/dashboard.html
```

- **Pengalaman**: tiap catatan berhasil/gagal pada tugas mirip menaikkan/menurunkan peringkat skill itu (maks ±0.3).
- **Celah**: pekerjaan tanpa skill yang cocok dicatat otomatis; yang muncul ≥2 kali menjadi usulan skill baru.
- **Dashboard**: katalog skill, uji pekerjaan interaktif (skor sama dengan CLI), papan pengalaman, usulan evolusi, dan cache rekomendasi GitHub. Satu file HTML, tanpa server.

Memori disimpan di `~/.claude/pengelola-skill/memori.json` (ubah dengan env `PENGELOLA_SKILL_MEMORI`).

Set `GITHUB_TOKEN` (opsional) agar tidak cepat terkena batas rate pencarian GitHub (10 kueri/menit tanpa token).
