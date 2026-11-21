"""
Narasi opsional dari LLM lokal (Ollama, gratis & offline). Bila Ollama tidak dikonfigurasi, tidak terjangkau,
atau narasinya memuat angka yang tidak ada di bukti, narasi template dipakai.
"""

import json
import re
from typing import Tuple

import httpx

from config import settings
from insight.framework import narrative
from utils.logger import setup_logging

logger = setup_logging()
NUM = re.compile(r"-?\d+(?:[.,]\d+)?")
SMALL_INTS = {str(i) for i in range(0, 11)}  # "3 alternatif", "5 hari" boleh tanpa bukti

PROMPT = """Anda analis trading yang disiplin. Tulis ringkasan keputusan 4-6 kalimat dalam bahasa Indonesia.
Aturan keras:
- Gunakan HANYA fakta dan angka yang ada di BUKTI di bawah. Jangan menambah angka, harga, atau persentase baru.
- Sebutkan rekomendasi, alasan utamanya, risiko terbesar (pre-mortem), dan kapan keputusan dibatalkan.
- Jangan memberi jaminan keuntungan.

BUKTI (JSON):
{evidence}
"""


def _norm(n: str) -> str:
    n = n.replace(",", ".").lstrip("-")
    return n.rstrip("0").rstrip(".") if "." in n else n


def grounded(text: str, evidence_text: str) -> bool:
    """Setiap angka di narasi harus muncul di bukti (toleransi pembulatan 1 desimal)."""
    allowed = {_norm(n) for n in NUM.findall(evidence_text)}
    allowed |= {_norm(f"{float(n):.1f}") for n in list(allowed) if n.replace(".", "", 1).isdigit()}
    allowed |= {str(round(float(n))) for n in list(allowed) if n.replace(".", "", 1).isdigit()}
    for n in NUM.findall(text):
        k = _norm(n)
        if k not in allowed and k not in SMALL_INTS:
            return False
    return True


def evidence_of(fw: dict) -> str:
    keep = {
        "jenis": fw["jenis"], "masalah": fw["masalah"], "fakta": fw["fakta"],
        "ringkasan_bukti": fw["hipotesis"]["ringkasan"],
        "bukti": [b["teks"] for b in fw["hipotesis"]["bukti"][:6]],
        "alternatif_teratas": [{k: a[k] for k in ("judul", "alasan", "skor", "risiko", "titik_batal")}
                               for a in fw["alternatif"][:3]],
        "pre_mortem": fw["keputusan"]["pre_mortem"],
    }
    return json.dumps(keep, ensure_ascii=False, default=str)


async def narrate(fw: dict) -> Tuple[str, str]:
    fallback = narrative(fw)
    if not settings.ollama_url:
        return fallback, "template"
    ev = evidence_of(fw)
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as c:
            r = await c.post(f"{settings.ollama_url.rstrip('/')}/api/generate", json={
                "model": settings.ollama_model, "prompt": PROMPT.format(evidence=ev), "stream": False,
                "options": {"temperature": 0.2}})
            r.raise_for_status()
            text = (r.json().get("response") or "").strip()
    except Exception as e:
        logger.warning(f"⚠️ LLM lokal tidak tersedia: {e}")
        return fallback, "template (LLM tidak terjangkau)"
    if not text:
        return fallback, "template (LLM kosong)"
    if not grounded(text, ev):
        logger.warning("⚠️ Narasi LLM ditolak: memuat angka yang tidak ada di bukti")
        return fallback, "template (LLM ditolak: angka tak berdasar)"
    return text, f"llm:{settings.ollama_model}"
