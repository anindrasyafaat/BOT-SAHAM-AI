"""
Notifikasi: Telegram, Discord, dan browser (lewat WebSocket), plus price alert.
Pengaturan, alert, dan riwayat disimpan ke data/notifications.json agar bertahan setelah restart.
"""

import json
import uuid
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from config import settings
from utils.logger import setup_logging

logger = setup_logging()

STORE = Path("data/notifications.json")
DEFAULT_SETTINGS = {
    "telegram_enabled": False,
    "discord_enabled": False,
    "browser_notifications_enabled": True,
    "signal_notifications": True,
    "price_alerts": True,
}


def configured(value: Optional[str]) -> bool:
    """Placeholder dari .env.example ('your_...') dianggap belum diisi."""
    return bool(value) and not value.startswith("your_")


def _load() -> dict:
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("settings", dict(DEFAULT_SETTINGS))
    data.setdefault("alerts", [])
    data.setdefault("history", [])
    return data


class NotificationManager:
    """Satu state bersama untuk seluruh proses."""

    websocket_manager = None  # di-set main.py saat startup
    _state: Optional[dict] = None

    @property
    def state(self) -> dict:
        if NotificationManager._state is None:
            NotificationManager._state = _load()
        return NotificationManager._state

    def save(self):
        STORE.parent.mkdir(parents=True, exist_ok=True)
        self.state["history"] = self.state["history"][-500:]
        tmp = STORE.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(STORE)

    # ---------- channel ----------
    def channels(self) -> List[dict]:
        s = self.state["settings"]
        return [
            {"name": "telegram", "display_name": "Telegram", "enabled": s["telegram_enabled"],
             "ready": configured(settings.telegram_bot_token) and configured(settings.telegram_chat_id),
             "requirements": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]},
            {"name": "discord", "display_name": "Discord", "enabled": s["discord_enabled"],
             "ready": configured(settings.discord_webhook_url), "requirements": ["DISCORD_WEBHOOK_URL"]},
            {"name": "browser", "display_name": "Browser", "enabled": s["browser_notifications_enabled"],
             "ready": True, "requirements": []},
        ]

    async def _send(self, channel: str, title: str, message: str, payload: dict) -> str:
        if channel == "telegram":
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                                 json={"chat_id": settings.telegram_chat_id, "text": f"{title}\n{message}"})
                r.raise_for_status()
        elif channel == "discord":
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(settings.discord_webhook_url, json={"content": f"**{title}**\n{message}"})
                r.raise_for_status()
        elif channel == "browser":
            if not self.websocket_manager:
                raise RuntimeError("websocket belum siap")
            await self.websocket_manager.broadcast({"type": "notification", "data": payload}, channel="signals")
        return "sent"

    async def notify(self, type_: str, title: str, message: str, symbol: Optional[str] = None,
                     priority: str = "medium", channels: Optional[List[str]] = None) -> List[dict]:
        targets = channels or [c["name"] for c in self.channels() if c["enabled"] and c["ready"]]
        results = []
        for ch in targets:
            entry = {"id": uuid.uuid4().hex[:12], "type": type_, "title": title, "message": message,
                     "channel": ch, "symbol": symbol, "priority": priority, "sent_at": datetime.now().isoformat()}
            try:
                entry["status"] = await self._send(ch, title, message, entry)
            except Exception as e:
                entry["status"], entry["error"] = "failed", str(e)
                logger.warning(f"⚠️ Notifikasi {ch} gagal: {e}")
            self.state["history"].append(entry)
            results.append(entry)
        self.save()
        return results

    async def send_signal_alert(self, signal, message: str):
        if self.state["settings"]["signal_notifications"]:
            await self.notify("signal", f"Sinyal {signal.signal_type.value} {signal.symbol}", message.strip(),
                              symbol=signal.symbol, priority="high")

    # ---------- price alert ----------
    def add_alert(self, symbol: str, alert_type: str, target_price: Optional[float],
                  percent_change: Optional[float]) -> dict:
        alert = {"alert_id": uuid.uuid4().hex[:12], "symbol": symbol.upper(), "alert_type": alert_type,
                 "target_price": target_price, "percent_change": percent_change, "status": "active",
                 "created_at": datetime.now().isoformat()}
        self.state["alerts"].append(alert)
        self.save()
        return alert

    def delete_alert(self, alert_id: str) -> bool:
        before = len(self.state["alerts"])
        self.state["alerts"] = [a for a in self.state["alerts"] if a["alert_id"] != alert_id]
        self.save()
        return len(self.state["alerts"]) < before

    @staticmethod
    def alert_hit(alert: dict, quote: dict) -> bool:
        price = quote.get("current_price")
        if price is None:
            return False
        if alert["alert_type"] == "above":
            return price >= alert["target_price"]
        if alert["alert_type"] == "below":
            return price <= alert["target_price"]
        return abs(quote.get("change_percent") or 0) >= abs(alert["percent_change"] or 0)  # percent_change

    async def check_price_alerts(self, quotes: Dict[str, dict]):
        if not self.state["settings"]["price_alerts"]:
            return
        for a in self.state["alerts"]:
            q = quotes.get(a["symbol"])
            if a["status"] == "active" and q and self.alert_hit(a, q):
                a.update(status="triggered", triggered_at=datetime.now().isoformat(), triggered_price=q["current_price"])
                await self.notify("price_alert", f"Price alert {a['symbol']}",
                                  f"{a['symbol']} {a['alert_type']} {a['target_price'] or a['percent_change']} "
                                  f"(harga {q['current_price']:.4g})", symbol=a["symbol"])
        self.save()

    def stats(self) -> dict:
        h = self.state["history"]
        now = datetime.now()
        since = lambda d: [x for x in h if datetime.fromisoformat(x["sent_at"]) >= now - d]
        ok = [x for x in h if x["status"] == "sent"]
        top = lambda key: (Counter(x[key] for x in h if x.get(key)).most_common(1) or [(None, 0)])[0][0]
        return {
            "total_sent_today": len(since(timedelta(days=1))),
            "total_sent_week": len(since(timedelta(days=7))),
            "total": len(h),
            "success_rate": round(100 * len(ok) / len(h), 1) if h else None,
            "most_active_channel": top("channel"),
            "most_common_type": top("type"),
            "most_active_symbol": top("symbol"),
            "active_alerts": sum(a["status"] == "active" for a in self.state["alerts"]),
        }
