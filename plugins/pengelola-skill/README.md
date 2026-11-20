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

Set `GITHUB_TOKEN` (opsional) agar tidak cepat terkena batas rate pencarian GitHub (10 kueri/menit tanpa token).
