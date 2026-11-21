"""
Notifications Routes untuk Trading Command Center
"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, model_validator

from notifications.manager import NotificationManager

router = APIRouter()
nm = NotificationManager()


class NotificationSettings(BaseModel):
    telegram_enabled: bool = False
    discord_enabled: bool = False
    browser_notifications_enabled: bool = True
    signal_notifications: bool = True
    price_alerts: bool = True


class PriceAlert(BaseModel):
    symbol: str
    alert_type: Literal["above", "below", "percent_change"]
    target_price: Optional[float] = None
    percent_change: Optional[float] = None

    @model_validator(mode="after")
    def _need_value(self):
        if self.alert_type == "percent_change" and self.percent_change is None:
            raise ValueError("percent_change wajib untuk alert_type percent_change")
        if self.alert_type != "percent_change" and (self.target_price is None or self.target_price <= 0):
            raise ValueError("target_price > 0 wajib untuk alert above/below")
        return self


class TestNotification(BaseModel):
    channel: Literal["telegram", "discord", "browser"]
    message: str = "Tes notifikasi dari Trading Command Center"


@router.get("/settings")
async def get_notification_settings():
    return {"status": "success", "data": nm.state["settings"]}


@router.post("/settings")
async def update_notification_settings(body: NotificationSettings):
    nm.state["settings"].update(body.model_dump())
    nm.save()
    return {"status": "success", "message": "Pengaturan notifikasi disimpan", "data": nm.state["settings"]}


@router.get("/channels")
async def get_notification_channels():
    data = nm.channels()
    return {"status": "success", "data": data, "total": len(data)}


@router.get("/history")
async def get_notification_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    channel: Optional[str] = Query(None),
):
    items = [n for n in reversed(nm.state["history"]) if not channel or n["channel"] == channel]
    return {"status": "success", "data": items[offset:offset + limit], "total": len(items),
            "limit": limit, "offset": offset}


@router.post("/test")
async def send_test_notification(body: TestNotification):
    ch = next(c for c in nm.channels() if c["name"] == body.channel)
    if not ch["ready"]:
        raise HTTPException(status_code=400, detail=f"Channel {body.channel} belum dikonfigurasi: {', '.join(ch['requirements'])}")
    result = (await nm.notify("test", "Tes notifikasi", body.message, channels=[body.channel]))[0]
    if result["status"] != "sent":
        raise HTTPException(status_code=502, detail=f"Gagal mengirim: {result.get('error')}")
    return {"status": "success", "data": result}


@router.post("/price-alerts")
async def create_price_alert(alert: PriceAlert):
    data = nm.add_alert(alert.symbol, alert.alert_type, alert.target_price, alert.percent_change)
    return {"status": "success", "message": f"Price alert dibuat untuk {data['symbol']}", "data": data}


@router.get("/price-alerts")
async def get_price_alerts(symbol: Optional[str] = Query(None), active_only: bool = Query(False)):
    alerts = [a for a in nm.state["alerts"]
              if (not symbol or a["symbol"] == symbol.upper()) and (not active_only or a["status"] == "active")]
    return {"status": "success", "data": alerts, "total": len(alerts)}


@router.delete("/price-alerts/{alert_id}")
async def delete_price_alert(alert_id: str):
    if not nm.delete_alert(alert_id):
        raise HTTPException(status_code=404, detail="Alert tidak ditemukan")
    return {"status": "success", "message": f"Price alert {alert_id} dihapus"}


@router.get("/stats")
async def get_notification_stats():
    return {"status": "success", "data": nm.stats()}
