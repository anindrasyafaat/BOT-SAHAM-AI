"""
Integrasi AI Brain dengan database SQLite sungguhan: sinyal tertutup -> performa -> StrategyConfig berubah.
Proses terpisah (subprocess) karena DATABASE_URL dibaca saat modul database diimpor.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

SCRIPT = textwrap.dedent('''
    import asyncio
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from database.connection import AsyncSessionLocal, init_database
    from models.signals import TradingSignal, SignalType, SignalStatus, TimeFrame, StrategyConfig
    from signals.generator import SignalGenerator

    class WS:
        events = []
        async def broadcast(self, msg, channel=None):
            self.events.append(msg)

    def sig(strategy, pnl):
        now = datetime.now()
        return TradingSignal(symbol="TEST", signal_type=SignalType.BUY, strategy_name=strategy, timeframe=TimeFrame.D1,
                             confidence_score=80, entry_price=100, stop_loss=95, target_price_1=110,
                             status=SignalStatus.STOPPED_OUT if pnl < 0 else SignalStatus.TARGET_HIT,
                             generated_at=now - timedelta(days=1), closed_at=now, pnl_percent=pnl, pnl_amount=pnl)

    async def main():
        await init_database()
        ws = WS()
        gen = SignalGenerator(market_data_manager=None, websocket_manager=ws)
        await gen._load_strategy_configs()
        async with AsyncSessionLocal() as s:
            # EMA_Crossover: 30 sinyal, win rate 30%, rugi -> harus lebih selektif
            s.add_all([sig("EMA_Crossover", 1.0) for _ in range(9)] + [sig("EMA_Crossover", -2.0) for _ in range(21)])
            # Strategi tanpa config bawaan: 25 sinyal untung -> config dibuat & ambang turun
            s.add_all([sig("Fundamental_Analysis", 3.0) for _ in range(18)] + [sig("Fundamental_Analysis", -1.0) for _ in range(7)])
            await s.commit()
        before = gen.strategy_configs["EMA_Crossover"]["min_confidence"]
        await gen._update_performance_metrics()
        async with AsyncSessionLocal() as s:
            ema = (await s.execute(select(StrategyConfig).where(StrategyConfig.strategy_name == "EMA_Crossover"))).scalar_one()
            fa = (await s.execute(select(StrategyConfig).where(StrategyConfig.strategy_name == "Fundamental_Analysis"))).scalar_one()
        assert float(ema.min_confidence) == before + 2, (before, ema.min_confidence)
        assert float(fa.min_confidence) == gen.parameters.min_confidence - 1, fa.min_confidence
        assert gen.strategy_configs["EMA_Crossover"]["min_confidence"] == before + 2
        assert {e["strategy"] for e in gen.brain_log} == {"EMA_Crossover", "Fundamental_Analysis"}
        assert any(m["type"] == "brain_update" for m in ws.events)
        print("BRAIN_OK", before, float(ema.min_confidence), float(fa.min_confidence))

    asyncio.run(main())
''')


def test_brain_learns_from_closed_signals(tmp_path: Path):
    backend = Path(__file__).resolve().parents[1]
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path}/brain.db", "PYTHONPATH": str(backend)}
    r = subprocess.run([sys.executable, "-c", SCRIPT], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and "BRAIN_OK" in r.stdout, r.stdout[-2000:] + r.stderr[-3000:]
