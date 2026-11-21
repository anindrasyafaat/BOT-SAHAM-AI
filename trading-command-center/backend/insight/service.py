"""
Menghubungkan mesin Generate dengan sistem: mengumpulkan fakta (data pasar, sinyal, portofolio),
pengalaman (pola sinyal tertutup, analog historis), menyimpan riwayat, dan menilai hasil otomatis.
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import AsyncSessionLocal
from insight import framework
from insight.analogs import analog_stats, analog_table
from insight.context import context_at
from insight.llm import narrate
from insight.patterns import matching, mine
from models.insight import Generation, SignalContext
from models.portfolio import Position
from models.signals import SignalStatus, TradingSignal
from utils.logger import setup_logging

logger = setup_logging()
AUTO_EVAL_DAYS = 7          # ±5 hari perdagangan
DIRECTIONAL = {"LAKUKAN": 1, "BERTAHAP": 1, "HINDARI": -1, "LINDUNGI": -1, "TUNDA": 0}
_analog_cache = {"key": None, "table": None}


class InsightError(ValueError):
    pass


# ---------------------------------------------------------------- pengalaman

async def experience_records(session: AsyncSession) -> list:
    rows = (await session.execute(
        select(TradingSignal.strategy_name, TradingSignal.pnl_percent, SignalContext.context)
        .join(SignalContext, SignalContext.signal_id == TradingSignal.id, isouter=True)
        .where(TradingSignal.status != SignalStatus.ACTIVE, TradingSignal.pnl_percent.is_not(None))
    )).all()
    return [{"strategy": s, "pnl": float(p), "context": json.loads(c) if c else {}} for s, p, c in rows]


async def analogs(mdm):
    key = mdm.last_refresh
    if _analog_cache["key"] != key or _analog_cache["table"] is None:
        _analog_cache["table"] = await asyncio.to_thread(analog_table, dict(mdm.history))
        _analog_cache["key"] = key
    return _analog_cache["table"]


def _fear_greed_value(mdm) -> Optional[float]:
    from routes.market_data import fear_greed
    fg = fear_greed(mdm.get_all_market_data(), mdm.history)
    return fg["value"] if fg else None


async def ensure_contexts(mdm, limit: int = 500):
    """Lengkapi konteks untuk sinyal yang belum punya (baru maupun lama) dari candle per tanggal sinyal."""
    if not mdm or not mdm.history:
        return 0
    fg = _fear_greed_value(mdm)
    async with AsyncSessionLocal() as s:
        rows = (await s.execute(
            select(TradingSignal.id, TradingSignal.symbol, TradingSignal.generated_at)
            .join(SignalContext, SignalContext.signal_id == TradingSignal.id, isouter=True)
            .where(SignalContext.signal_id.is_(None)).limit(limit))).all()
        recent = datetime.now() - timedelta(hours=1)
        for sid, sym, when in rows:
            fresh = when and when >= recent  # sinyal baru: fear&greed saat ini relevan
            ctx = context_at(sym, mdm.history.get(sym), when=when, fear_greed=fg if fresh else None)
            s.add(SignalContext(signal_id=sid, context=json.dumps(ctx)))
        await s.commit()
    return len(rows)


async def operator_stats(session: AsyncSession, kind: str) -> dict:
    rows = (await session.execute(
        select(Generation.chosen_operator, Generation.outcome)
        .where(Generation.kind == kind, Generation.chosen_operator.is_not(None), Generation.outcome.is_not(None))
    )).all()
    stats = {}
    for op, out in rows:
        s, f = stats.get(op, (0, 0))
        stats[op] = (s + (out == "berhasil"), f + (out == "gagal"))
    return stats


# ---------------------------------------------------------------- tafsir kasus

def resolve_symbol(mdm, text: str, explicit: bool = False) -> Optional[str]:
    """explicit=False (teks bebas): hanya token HURUF BESAR atau ber-sufiks (.JK/-USD) yang dianggap ticker,
    agar kata biasa seperti "ada" / "net" tidak terbaca sebagai ADAUSDT / NET."""
    supported = mdm.market_type_of
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9.\-]{1,14}", text or ""):
        if not explicit and not (tok.isupper() or "." in tok or "-" in tok):
            continue
        t = tok.upper()
        for cand in (t, f"{t}.JK", f"{t}USDT", t.replace("-USD", "USDT")):
            if cand in supported:
                return cand
    return None


def resolve_strategy(gen, text: str) -> Optional[str]:
    low = (text or "").lower()
    names = set(gen.strategy_configs) if gen else set()
    return next((n for n in sorted(names, key=len, reverse=True) if n.lower() in low or n.lower().replace("_", " ") in low), None)


def interpret(kind, symbol, strategy, text, mdm, gen):
    """Kasus 'bebas' ditafsirkan ke jenis konkret dari teksnya."""
    if kind != "bebas":
        return kind, symbol, strategy
    strategy = strategy or resolve_strategy(gen, text)
    symbol = symbol or resolve_symbol(mdm, text)
    if symbol:
        return "peluang", symbol, strategy
    if strategy:
        return "strategi", symbol, strategy
    return "portofolio", None, None


# ---------------------------------------------------------------- fakta

async def facts_peluang(session, mdm, gen, symbol: str) -> dict:
    q = mdm.get_market_data(symbol)
    if not q:
        raise InsightError(f"Data pasar {symbol} belum tersedia")
    from news_sentiment.analyzer import SentimentAnalyzer
    news = await SentimentAnalyzer().get_news_sentiment(symbol)
    ctx = context_at(symbol, mdm.history.get(symbol), fear_greed=_fear_greed_value(mdm), news_sentiment=news)
    pos = (await session.execute(select(Position).where(Position.symbol == symbol))).scalar_one_or_none()
    sigs = [{"arah": s.signal_type.value, "strategi": s.strategy_name, "confidence": float(s.confidence_score)}
            for s in (gen.active_signals.get(symbol, []) if gen else [])]
    return {
        "simbol": symbol, "nama": q.get("name"), "harga": float(q["current_price"]),
        "perubahan_persen": round(float(q["change_percent"]), 2), "konteks": ctx,
        "sentimen_berita": round(news, 3) if news is not None else None, "sinyal_aktif": sigs,
        "posisi": {"jumlah": pos.quantity, "harga_rata": pos.avg_entry_price, "stop_loss": pos.stop_loss} if pos else None,
    }


async def facts_strategi(session, gen, name: str, records: list) -> dict:
    if not gen or name not in gen.strategy_configs:
        raise InsightError(f"Strategi {name!r} tidak dikenal")
    mine_ = [r for r in records if r["strategy"] == name]
    wins = sum(r["pnl"] > 0 for r in mine_)
    cfg = gen.strategy_configs[name]
    return {"strategi": name, "aktif": cfg["enabled"], "ambang_confidence": cfg["min_confidence"],
            "strategi_stat": {"tertutup": len(mine_), "win_rate": round(wins / len(mine_) * 100, 1) if mine_ else None,
                              "expectancy": round(sum(r["pnl"] for r in mine_) / len(mine_), 3) if mine_ else None}}


async def facts_portofolio(session, mdm) -> dict:
    from paper import broker
    summ = await broker.summary(session, mdm)
    pos = await broker.positions(session, mdm)
    trades = await broker._all_trades(session)
    perf = broker.performance(trades, broker.equity_series(trades, mdm.history, mdm.to_idr, 90))
    total = summ["total_value"] or 1
    biggest = max(pos, key=lambda p: p["market_value"], default=None)
    return {"portofolio": {
        "nilai_total": round(summ["total_value"]), "kas": round(summ["cash_balance"]),
        "total_pnl_persen": round(summ["total_pnl_percent"], 2), "drawdown_persen": round(perf["max_drawdown"], 2),
        "jumlah_posisi": len(pos), "posisi_rugi": sum(p["unrealized_pnl"] < 0 for p in pos),
        "posisi_tanpa_sl": sum(not p["stop_loss"] for p in pos),
        "posisi_terbesar": biggest["symbol"] if biggest else None,
        "konsentrasi_terbesar_persen": round(biggest["market_value"] / total * 100, 1) if biggest else 0.0,
    }}


# ---------------------------------------------------------------- generate

async def generate(app, kind: str, symbol: Optional[str], strategy: Optional[str], text: str) -> dict:
    mdm = getattr(app.state, "market_data_manager", None)
    gen = getattr(app.state, "signal_generator", None)
    if not mdm or not mdm.market_data_cache:
        raise InsightError("Data pasar belum siap, coba lagi sebentar")
    if kind not in framework.KINDS:
        raise InsightError(f"jenis harus salah satu dari {framework.KINDS}")
    if symbol:
        symbol = resolve_symbol(mdm, symbol, explicit=True)
        if not symbol:
            raise InsightError("Simbol tidak termasuk daftar yang dipantau")
    eff_kind, symbol, strategy = interpret(kind, symbol, strategy, text, mdm, gen)
    if eff_kind == "peluang" and not symbol:
        raise InsightError("Kasus peluang butuh simbol")
    if eff_kind == "strategi" and not strategy:
        raise InsightError("Kasus strategi butuh nama strategi")

    async with AsyncSessionLocal() as session:
        records = await experience_records(session)
        patterns = mine(records)
        if eff_kind == "peluang":
            facts = await facts_peluang(session, mdm, gen, symbol)
            table = await analogs(mdm)
            experience = {"analog": analog_stats(table, facts["konteks"]), "pola": matching(patterns, facts["konteks"]),
                          "total_pengalaman": patterns["total_pengalaman"]}
        elif eff_kind == "strategi":
            facts = await facts_strategi(session, gen, strategy, records)
            experience = {"analog": None, "total_pengalaman": patterns["total_pengalaman"], "pola": {
                "gagal": [p for p in patterns["gagal"] if p["kondisi"].get("strategi") == strategy],
                "berhasil": [p for p in patterns["berhasil"] if p["kondisi"].get("strategi") not in (None, strategy)]}}
        else:
            facts = await facts_portofolio(session, mdm)
            experience = {"analog": None, "pola": {"berhasil": [], "gagal": []}, "total_pengalaman": patterns["total_pengalaman"]}

        problem = text.strip() or {"peluang": f"Apakah perlu masuk/keluar {symbol}?",
                                   "strategi": f"Apa yang harus dilakukan dengan strategi {strategy}?",
                                   "portofolio": "Bagaimana mengelola risiko portofolio sekarang?"}[eff_kind]
        fw = framework.build(eff_kind, facts, experience, await operator_stats(session, eff_kind), problem)
        if kind == "bebas":
            fw["ditafsirkan_sebagai"] = eff_kind
        text_out, source = await narrate(fw)
        g = Generation(kind=eff_kind, symbol=symbol, problem=problem, output=json.dumps(fw, default=str),
                       narrative=text_out, narrative_source=source,
                       price_at=facts.get("harga") if eff_kind == "peluang" else None)
        session.add(g)
        await session.commit()
        await session.refresh(g)
        return g.to_dict(full=True)


def judge(operator: str, ret_pct: float) -> Optional[str]:
    """Penilaian otomatis arah keputusan vs gerak harga setelah horizon."""
    d = DIRECTIONAL.get(operator)
    if d is None:
        return None  # GANTI / RISET dinilai manual
    if d == 0:  # menunggu benar bila tidak tertinggal kenaikan besar
        return "berhasil" if ret_pct <= 2 else "gagal"
    return "berhasil" if ret_pct * d > 0 else "gagal"


async def evaluate_due(mdm) -> int:
    if not mdm:
        return 0
    cutoff = datetime.now() - timedelta(days=AUTO_EVAL_DAYS)
    n = 0
    async with AsyncSessionLocal() as s:
        due = (await s.execute(select(Generation).where(
            Generation.kind == "peluang", Generation.chosen_operator.is_not(None), Generation.outcome.is_(None),
            Generation.created_at <= cutoff))).scalars().all()
        for g in due:
            q = mdm.get_market_data(g.symbol)
            if not q or not g.price_at:
                continue
            ret = (float(q["current_price"]) / g.price_at - 1) * 100
            verdict = judge(g.chosen_operator, ret)
            if verdict:
                g.outcome, g.outcome_source, g.evaluated_at = verdict, "otomatis", datetime.now()
                g.note = f"Harga {ret:+.2f}% setelah {AUTO_EVAL_DAYS} hari"
                n += 1
        await s.commit()
    return n
