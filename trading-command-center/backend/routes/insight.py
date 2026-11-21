"""
Generate: kerangka berpikir dari pengalaman + alternatif solusi (insight/).
"""

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from database.connection import AsyncSessionLocal
from insight import service
from insight.analogs import analog_stats
from insight.context import context_at
from insight.framework import OPERATORS
from insight.patterns import mine
from models.insight import Generation

router = APIRouter()


class GenerateIn(BaseModel):
    jenis: Literal["peluang", "strategi", "portofolio", "bebas"]
    simbol: Optional[str] = Field(default=None, max_length=20)
    strategi: Optional[str] = Field(default=None, max_length=60)
    teks: str = Field(default="", max_length=1000)


class ChooseIn(BaseModel):
    operator: Literal["LAKUKAN", "BERTAHAP", "TUNDA", "GANTI", "LINDUNGI", "HINDARI", "RISET"]


class OutcomeIn(BaseModel):
    hasil: Literal["berhasil", "gagal"]
    catatan: str = Field(default="", max_length=500)


@router.post("/generate")
async def generate(body: GenerateIn, request: Request):
    try:
        data = await service.generate(request.app, body.jenis, body.simbol, body.strategi, body.teks)
    except service.InsightError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "data": data}


@router.get("/patterns")
async def patterns():
    async with AsyncSessionLocal() as s:
        return {"status": "success", "data": mine(await service.experience_records(s))}


@router.get("/analogs/{symbol}")
async def analogs(symbol: str, request: Request):
    mdm = getattr(request.app.state, "market_data_manager", None)
    sym = service.resolve_symbol(mdm, symbol, explicit=True) if mdm else None
    if not sym or sym not in mdm.history:
        raise HTTPException(status_code=404, detail="Simbol tidak dipantau atau data belum siap")
    ctx = context_at(sym, mdm.history[sym])
    return {"status": "success", "data": {"simbol": sym, "konteks": ctx,
                                          "analog": analog_stats(await service.analogs(mdm), ctx)}}


@router.get("/operators")
async def operators():
    return {"status": "success", "data": OPERATORS}


@router.get("/history")
async def history(limit: int = Query(30, ge=1, le=200)):
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(select(Generation).order_by(desc(Generation.id)).limit(limit))).scalars().all()
        stats = {k: await service.operator_stats(s, k) for k in ("peluang", "strategi", "portofolio")}
    return {"status": "success", "data": [g.to_dict() for g in rows],
            "rekam_jejak_operator": {k: {op: {"berhasil": a, "gagal": b} for op, (a, b) in v.items()} for k, v in stats.items()}}


@router.get("/{gen_id}")
async def get_one(gen_id: int):
    async with AsyncSessionLocal() as s:
        g = await s.get(Generation, gen_id)
        if not g:
            raise HTTPException(status_code=404, detail="Tidak ditemukan")
        return {"status": "success", "data": g.to_dict(full=True)}


@router.post("/{gen_id}/choose")
async def choose(gen_id: int, body: ChooseIn):
    async with AsyncSessionLocal() as s:
        g = await s.get(Generation, gen_id)
        if not g:
            raise HTTPException(status_code=404, detail="Tidak ditemukan")
        if g.outcome:
            raise HTTPException(status_code=409, detail="Keputusan sudah dinilai, tidak bisa diganti")
        g.chosen_operator = body.operator
        await s.commit()
        return {"status": "success", "data": g.to_dict()}


@router.post("/{gen_id}/outcome")
async def outcome(gen_id: int, body: OutcomeIn):
    async with AsyncSessionLocal() as s:
        g = await s.get(Generation, gen_id)
        if not g:
            raise HTTPException(status_code=404, detail="Tidak ditemukan")
        if not g.chosen_operator:
            raise HTTPException(status_code=409, detail="Pilih alternatif dulu sebelum menandai hasil")
        g.outcome, g.outcome_source, g.evaluated_at, g.note = body.hasil, "manual", datetime.now(), body.catatan or g.note
        await s.commit()
        return {"status": "success", "data": g.to_dict()}
