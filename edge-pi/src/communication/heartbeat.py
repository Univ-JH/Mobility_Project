import asyncio
import httpx


async def start(backend_url: str, device_id: str, token: str) -> None:
    """Send heartbeat to backend on startup and every 30s."""
    while True:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{backend_url}/v1/devices/heartbeat",
                    json={"deviceId": device_id},
                    headers={"Authorization": f"Bearer {token}"},
                )
            print(f"[HEARTBEAT] ✅ 백엔드 heartbeat 전송 완료 (deviceId: {device_id})")
        except Exception as e:
            print(f"[HEARTBEAT] ⚠️ 전송 실패 (무시, 30초 후 재시도): {e}")
        await asyncio.sleep(30)
