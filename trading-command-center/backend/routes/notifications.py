"""
Notifications Routes untuk Trading Command Center
API endpoints untuk notification management
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from utils.logger import setup_logging

logger = setup_logging()
router = APIRouter()


class NotificationSettings(BaseModel):
    telegram_enabled: bool = False
    discord_enabled: bool = False
    browser_notifications_enabled: bool = True
    sound_alerts_enabled: bool = True
    email_notifications_enabled: bool = False
    
    # Notification preferences
    signal_notifications: bool = True
    price_alerts: bool = True
    news_notifications: bool = False
    market_summary_notifications: bool = False
    
    # Frequency settings
    notification_frequency: str = "immediate"  # immediate, hourly, daily
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"


class PriceAlert(BaseModel):
    symbol: str
    target_price: float
    current_price: float
    alert_type: str  # above, below, percent_change
    percent_change: Optional[float] = None
    is_active: bool = True


@router.get("/settings")
async def get_notification_settings():
    """Get current notification settings"""
    try:
        # Mock settings untuk demo
        settings = NotificationSettings()
        
        return {
            "status": "success",
            "data": settings.dict()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting notification settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/settings")
async def update_notification_settings(settings: NotificationSettings):
    """Update notification settings"""
    try:
        # Simpan settings (dalam production, simpan ke database)
        
        return {
            "status": "success",
            "message": "Notification settings updated successfully",
            "data": settings.dict()
        }
        
    except Exception as e:
        logger.error(f"❌ Error updating notification settings: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/channels")
async def get_notification_channels():
    """Get available notification channels"""
    try:
        channels = [
            {
                "name": "telegram",
                "display_name": "Telegram",
                "description": "Receive notifications via Telegram bot",
                "status": "configurable",
                "requirements": ["Bot Token", "Chat ID"]
            },
            {
                "name": "discord",
                "display_name": "Discord",
                "description": "Receive notifications via Discord webhook",
                "status": "configurable",
                "requirements": ["Webhook URL"]
            },
            {
                "name": "browser",
                "display_name": "Browser Notifications",
                "description": "Native browser push notifications",
                "status": "ready",
                "requirements": []
            },
            {
                "name": "sound",
                "display_name": "Sound Alerts",
                "description": "Audio alerts for new signals",
                "status": "ready",
                "requirements": []
            },
            {
                "name": "email",
                "display_name": "Email",
                "description": "Email notifications for important events",
                "status": "configurable",
                "requirements": ["Email Address", "SMTP Configuration"]
            }
        ]
        
        return {
            "status": "success",
            "data": channels,
            "total": len(channels)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting notification channels: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history")
async def get_notification_history(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get notification history"""
    try:
        # Mock notification history untuk demo
        notifications = [
            {
                "id": "notif_001",
                "type": "signal",
                "title": "New BUY Signal - BBCA.JK",
                "message": "EMA Crossover strategy generated BUY signal for BBCA.JK with 85% confidence",
                "channel": "telegram",
                "status": "sent",
                "sent_at": "2024-01-27T14:30:00Z",
                "symbol": "BBCA.JK",
                "priority": "high"
            },
            {
                "id": "notif_002",
                "type": "price_alert",
                "title": "Price Alert - GOTO.JK",
                "message": "GOTO.JK has reached your target price of 125",
                "channel": "browser",
                "status": "sent",
                "sent_at": "2024-01-27T13:45:00Z",
                "symbol": "GOTO.JK",
                "priority": "medium"
            },
            {
                "id": "notif_003",
                "type": "market_summary",
                "title": "Market Summary - IHSG +0.8%",
                "message": "IHSG closed up 0.8% today with banking sector leading gains",
                "channel": "discord",
                "status": "sent",
                "sent_at": "2024-01-26T16:30:00Z",
                "symbol": "IHSG",
                "priority": "low"
            },
            {
                "id": "notif_004",
                "type": "signal",
                "title": "Signal Closed - BBRI.JK",
                "message": "BBRI.JK signal reached target price with +8.5% profit",
                "channel": "telegram",
                "status": "sent",
                "sent_at": "2024-01-26T11:20:00Z",
                "symbol": "BBRI.JK",
                "priority": "high"
            }
        ]
        
        # Apply channel filter
        if channel:
            notifications = [n for n in notifications if n["channel"] == channel]
        
        # Apply pagination
        total = len(notifications)
        paginated_notifications = notifications[offset:offset + limit]
        
        return {
            "status": "success",
            "data": paginated_notifications,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting notification history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/test")
async def send_test_notification(
    channel: str,
    message: str = "This is a test notification from Trading Command Center",
    session: AsyncSession = Depends(get_db_session)
):
    """Send test notification untuk testing channels"""
    try:
        # Mock test notification
        test_result = {
            "channel": channel,
            "message": message,
            "status": "sent",
            "sent_at": "2024-01-27T15:30:00Z",
            "test_id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        return {
            "status": "success",
            "message": f"Test notification sent via {channel}",
            "data": test_result
        }
        
    except Exception as e:
        logger.error(f"❌ Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/price-alerts")
async def create_price_alert(alert: PriceAlert):
    """Create price alert untuk symbol"""
    try:
        # Mock alert creation
        alert_result = {
            "alert_id": f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "symbol": alert.symbol,
            "target_price": alert.target_price,
            "alert_type": alert.alert_type,
            "status": "active",
            "created_at": "2024-01-27T15:30:00Z"
        }
        
        return {
            "status": "success",
            "message": f"Price alert created for {alert.symbol}",
            "data": alert_result
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating price alert: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/price-alerts")
async def get_price_alerts(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    active_only: bool = Query(True, description="Show only active alerts"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get price alerts"""
    try:
        # Mock price alerts untuk demo
        alerts = [
            {
                "alert_id": "alert_001",
                "symbol": "BBCA.JK",
                "target_price": 10500,
                "current_price": 10250,
                "alert_type": "above",
                "status": "active",
                "created_at": "2024-01-25T10:30:00Z"
            },
            {
                "alert_id": "alert_002",
                "symbol": "GOTO.JK",
                "target_price": 120,
                "current_price": 125,
                "alert_type": "below",
                "status": "triggered",
                "created_at": "2024-01-24T14:15:00Z",
                "triggered_at": "2024-01-27T09:45:00Z"
            },
            {
                "alert_id": "alert_003",
                "symbol": "TLKM.JK",
                "target_price": 5000,
                "current_price": 4850,
                "alert_type": "above",
                "status": "active",
                "created_at": "2024-01-26T11:20:00Z"
            }
        ]
        
        # Apply filters
        if symbol:
            alerts = [alert for alert in alerts if alert["symbol"] == symbol]
        if active_only:
            alerts = [alert for alert in alerts if alert["status"] == "active"]
        
        return {
            "status": "success",
            "data": alerts,
            "total": len(alerts)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting price alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/price-alerts/{alert_id}")
async def delete_price_alert(alert_id: str):
    """Delete price alert"""
    try:
        return {
            "status": "success",
            "message": f"Price alert {alert_id} deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error deleting price alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_notification_stats(session: AsyncSession = Depends(get_db_session)):
    """Get notification statistics"""
    try:
        # Mock stats untuk demo
        stats = {
            "total_sent_today": 23,
            "total_sent_week": 156,
            "total_sent_month": 892,
            "success_rate": 98.5,
            "most_active_channel": "telegram",
            "most_common_type": "signal",
            "avg_notifications_per_day": 28.4,
            "peak_hour": "10:00-11:00",
            "most_active_symbol": "BBCA.JK"
        }
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting notification stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")