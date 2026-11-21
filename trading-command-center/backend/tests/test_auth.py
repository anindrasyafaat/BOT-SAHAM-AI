"""Auth: tes negatif DAN positif untuk setiap jalur (HTTP, WebSocket, login, startup produksi)."""

import pytest
from fastapi.testclient import TestClient

import auth
from config import settings




def test_token_roundtrip_and_expiry(monkeypatch):
    monkeypatch.setattr(settings, "app_password", "a")
    t = auth.issue(now=1000)
    assert auth.verify(t, now=1001) and not auth.verify(t, now=1000 + auth.TOKEN_TTL + 1)
    assert not auth.verify(t[:-2] + "xx", now=1001)               # tanda tangan dirusak
    assert not auth.verify("bukan-token", now=1001) and not auth.verify(None)
    monkeypatch.setattr(settings, "app_password", "b")              # ganti password -> token lama mati
    assert not auth.verify(t, now=1001)


def test_open_mode_and_production_guard(monkeypatch):
    monkeypatch.setattr(settings, "app_password", "")
    assert auth.verify(None)                                        # mode lokal tanpa password
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(RuntimeError):
        auth.check_startup()                                        # produksi wajib password


def test_http_requires_login(monkeypatch):
    monkeypatch.setattr(settings, "app_password", "rahasia-uji")
    auth._failures.clear()
    import main
    c = TestClient(main.app)  # tanpa `with`: lifespan (data pasar) tidak dijalankan
    assert c.get("/api/notifications/settings").status_code == 401           # negatif
    assert c.get("/api/notifications/settings", headers={"Authorization": "Bearer salah.token"}).status_code == 401
    assert c.post("/api/auth/login", json={"password": "keliru"}).status_code == 401
    tok = c.post("/api/auth/login", json={"password": "rahasia-uji"}).json()["token"]
    ok = c.get("/api/notifications/settings", headers={"Authorization": f"Bearer {tok}"})
    assert ok.status_code == 200                                              # positif
    st = c.get("/api/auth/status", headers={"Authorization": f"Bearer {tok}"}).json()
    assert st == {"required": True, "authenticated": True}
    # WebSocket: tanpa token ditolak, dengan token diterima
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("/ws") as ws:
            ws.receive_text()


def test_login_throttle(monkeypatch):
    monkeypatch.setattr(settings, "app_password", "x")
    auth._failures.clear()
    for _ in range(auth.MAX_FAILURES_PER_MIN):
        assert auth.login("salah", now=5000) is None
    assert auth.throttled(now=5001) and not auth.throttled(now=5070)
