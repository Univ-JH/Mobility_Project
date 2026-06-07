from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone


PRE_SHARED_TOKEN = "proto-secret-token-123"
USER_TOKEN = "mock-jwt-token"


def test_heartbeat_returns_200_with_valid_token(client):
    with patch("app.api.v1.devices.upsert_heartbeat", new_callable=AsyncMock):
        resp = client.post(
            "/v1/devices/heartbeat",
            json={"deviceId": "pi_01"},
            headers={"Authorization": f"Bearer {PRE_SHARED_TOKEN}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


def test_heartbeat_rejects_wrong_token(client):
    resp = client.post(
        "/v1/devices/heartbeat",
        json={"deviceId": "pi_01"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 403


def test_heartbeat_rejects_missing_token(client):
    resp = client.post("/v1/devices/heartbeat", json={"deviceId": "pi_01"})
    assert resp.status_code == 401


def test_get_available_devices_returns_list(client):
    mock_device = MagicMock()
    mock_device.deviceId = "pi_01"
    mock_device.lastHeartbeatAt = datetime.now(timezone.utc)

    with patch("app.api.v1.devices.get_available_devices", new_callable=AsyncMock, return_value=[mock_device]):
        resp = client.get(
            "/v1/devices/available",
            headers={"Authorization": f"Bearer {USER_TOKEN}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]["devices"]) == 1
    assert body["data"]["devices"][0]["deviceId"] == "pi_01"


def test_get_available_devices_rejects_missing_token(client):
    resp = client.get("/v1/devices/available")
    assert resp.status_code == 401
