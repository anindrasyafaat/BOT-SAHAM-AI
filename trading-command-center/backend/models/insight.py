"""Model fitur Generate: konteks pasar tiap sinyal (pengalaman) dan riwayat kerangka berpikir."""

import json

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from database.connection import Base


class SignalContext(Base):
    """Konteks pasar saat sinyal dibuat. Tabel terpisah agar database lama tidak perlu migrasi."""
    __tablename__ = "signal_contexts"

    signal_id = Column(Integer, primary_key=True)
    context = Column(Text, nullable=False)


class Generation(Base):
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True)
    kind = Column(String(20), nullable=False, index=True)
    symbol = Column(String(50), nullable=True)
    problem = Column(Text, nullable=False)
    output = Column(Text, nullable=False)          # JSON kerangka berpikir
    narrative = Column(Text, nullable=False)
    narrative_source = Column(String(80), nullable=False)
    price_at = Column(Float, nullable=True)         # untuk penilaian otomatis kasus peluang
    chosen_operator = Column(String(20), nullable=True)
    outcome = Column(String(10), nullable=True)     # berhasil / gagal
    outcome_source = Column(String(10), nullable=True)  # manual / otomatis
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    evaluated_at = Column(DateTime, nullable=True)

    def to_dict(self, full: bool = False) -> dict:
        d = {
            "id": self.id, "jenis": self.kind, "simbol": self.symbol, "masalah": self.problem,
            "narasi": self.narrative, "sumber_narasi": self.narrative_source, "harga_saat_itu": self.price_at,
            "dipilih": self.chosen_operator, "hasil": self.outcome, "sumber_hasil": self.outcome_source,
            "catatan": self.note, "dibuat": self.created_at.isoformat() if self.created_at else None,
            "dinilai": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }
        if full:
            d["kerangka"] = json.loads(self.output)
        return d
