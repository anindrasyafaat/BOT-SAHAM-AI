"""Tes logika inti tanpa jaringan/DB. Jalankan dari folder backend: python -m pytest -q"""

from datetime import date, datetime

import numpy as np
import pandas as pd

from config import settings
from models.portfolio import Trade
from news_sentiment.analyzer import score_text
from notifications.manager import NotificationManager, configured
from paper import broker
from routes.market_data import fear_greed
from routes.screener import rsi


def _trade(side, qty, price, day, fee=0.0, pnl=None, sym="BBCA.JK"):
    return Trade(symbol=sym, side=side, quantity=qty, price=price, fx_to_idr=1.0, fees_idr=fee,
                 realized_pnl_idr=pnl, executed_at=datetime.combine(day, datetime.min.time()))


def _hist(closes, start="2026-01-01"):
    idx = pd.date_range(start, periods=len(closes), freq="D")
    c = pd.Series(closes, index=idx, dtype=float)
    return pd.DataFrame({"Open": c, "High": c * 1.01, "Low": c * 0.99, "Close": c, "Volume": 1000.0})


def test_cash_and_equity_curve():
    d1, d3 = date(2026, 1, 1), date(2026, 1, 3)
    trades = [_trade("BUY", 100, 1000, d1, fee=150), _trade("SELL", 100, 1100, d3, fee=275, pnl=9725)]
    assert broker.cash_from_trades(trades) == settings.initial_capital - 100_000 - 150 + 110_000 - 275
    hist = {"BBCA.JK": _hist([1000, 1050, 1100, 1100])}
    curve = broker.equity_series(trades, hist, lambda s: 1.0, days=10, today=date(2026, 1, 4))
    assert curve[0]["date"] == "2026-01-01"  # mulai dari transaksi pertama
    assert curve[1]["value"] == settings.initial_capital - 100_150 + 100 * 1050  # mark-to-market hari ke-2
    assert curve[-1]["value"] == broker.cash_from_trades(trades)  # posisi sudah ditutup


def test_performance_stats():
    d = date(2026, 1, 1)
    trades = [_trade("SELL", 1, 1, d, pnl=300), _trade("SELL", 1, 1, d, pnl=-100), _trade("BUY", 1, 1, d)]
    equity = [{"value": v, "daily_return": r} for v, r in [(100, 0), (110, 10), (99, -10), (120, 21.2)]]
    p = broker.performance(trades, equity)
    assert p["win_rate"] == 50 and p["profit_factor"] == 3 and p["closed_trades"] == 2
    assert round(p["max_drawdown"], 2) == -10.0


def test_rsi_bounds():
    assert rsi(pd.Series(np.arange(1, 40, dtype=float))) == 100.0  # naik terus
    assert rsi(pd.Series(np.arange(40, 1, -1, dtype=float))) < 5   # turun terus
    assert rsi(pd.Series([1.0, 2.0])) is None


def test_fear_greed_range_and_direction():
    up = {f"S{i}": _hist(np.linspace(100, 150, 300)) for i in range(5)}
    down = {f"S{i}": _hist(np.linspace(150, 100, 300)) for i in range(5)}
    q_up = {s: {"change_percent": 1.0} for s in up}
    q_down = {s: {"change_percent": -1.0} for s in down}
    g, f = fear_greed(q_up, up), fear_greed(q_down, down)
    assert 0 <= f["value"] < g["value"] <= 100
    assert fear_greed({}, {}) is None


def test_sentiment_lexicon():
    assert score_text("Stocks surge to record high")[1] == "positive"
    assert score_text("Saham anjlok, investor rugi")[1] == "negative"
    assert score_text("Company holds annual meeting") == (0.0, "neutral")


def test_price_alert_and_placeholders():
    hit = NotificationManager.alert_hit
    assert hit({"alert_type": "above", "target_price": 100}, {"current_price": 101})
    assert not hit({"alert_type": "below", "target_price": 100}, {"current_price": 101})
    assert hit({"alert_type": "percent_change", "percent_change": 3}, {"current_price": 1, "change_percent": -3.5})
    assert not configured("your_telegram_bot_token_here") and configured("123:abc") and not configured(None)
