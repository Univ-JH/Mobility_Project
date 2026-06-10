"""
BLE 헬멧 모듈 테스트
- SmartHelmet_Alpha 장치 스캔
- GATT 연결 및 착용 상태 수신 (1바이트)
- 이벤트 패킷 수신 및 14바이트 구조체 파싱 검증

실행: python -m tests.test_ble_helmet  (edge-pi/ 루트에서)
"""
import asyncio
import struct
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.communication.comm_config import (
    BLE_DEVICE_NAME, STATUS_CHAR_UUID, EVENT_CHAR_UUID, EVENT_STRUCT_FORMAT
)

SCAN_TIMEOUT = 10.0
LISTEN_SEC   = 15

_status_received = False
_event_received  = False


def _on_status(sender, data):
    global _status_received
    if len(data) == 1:
        worn = (data[0] == 1)
        print(f"  [STATUS] 착용={worn}  (raw={data[0]})  ✅ 수신 OK")
        _status_received = True
    else:
        print(f"  [STATUS] ⚠️ 크기 오류: {len(data)}바이트")


def _on_event(sender, data):
    global _event_received
    if len(data) != 14:
        print(f"  [EVENT] ⚠️ 크기 오류: {len(data)}바이트 (기대 14)")
        return
    schema_ver, seq, timestamp, ride_id, event_label = struct.unpack(EVENT_STRUCT_FORMAT, data)
    is_accident = event_label in [1, 2, 3, 4]
    print(f"  [EVENT] schema={schema_ver} seq={seq} ts={timestamp}ms "
          f"ride={ride_id} label={event_label} accident={is_accident}  ✅ 파싱 OK")
    _event_received = True


async def test_scan():
    try:
        from bleak import BleakScanner
    except ImportError:
        print("[SKIP] bleak 미설치 — pip install bleak")
        return False

    print(f"\n[1] 장치 스캔: '{BLE_DEVICE_NAME}' ({SCAN_TIMEOUT}초)")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and BLE_DEVICE_NAME in d.name,
        timeout=SCAN_TIMEOUT
    )
    if device:
        print(f"  PASS — 장치 발견: {device.address}")
        return device
    else:
        print(f"  FAIL — 장치 미발견 (전원/BLE 상태 확인)")
        return None


async def test_connect_and_receive(device):
    from bleak import BleakClient

    print(f"\n[2] GATT 연결 및 Notification 구독 ({LISTEN_SEC}초 대기)")
    client = BleakClient(device)
    try:
        await client.connect()
        if not client.is_connected:
            print("  FAIL — 연결 실패")
            return

        print(f"  연결 성공: {device.address}")

        try:
            raw = await client.read_gatt_char(STATUS_CHAR_UUID)
            print(f"  [3] 초기 착용 상태 읽기: {raw[0] if raw else 'N/A'}")
        except Exception as e:
            print(f"  [3] 초기 읽기 실패: {e}")

        await client.start_notify(STATUS_CHAR_UUID, _on_status)
        await client.start_notify(EVENT_CHAR_UUID,  _on_event)

        print(f"  구독 시작 — {LISTEN_SEC}초 동안 알림 대기 (헬멧 착탈 또는 충격 유발)")
        await asyncio.sleep(LISTEN_SEC)

        try:
            await client.stop_notify(STATUS_CHAR_UUID)
            await client.stop_notify(EVENT_CHAR_UUID)
        except Exception:
            pass  # device may have already disconnected
    finally:
        try:
            await client.disconnect()
        except (EOFError, Exception):
            pass  # D-Bus EOF: device dropped connection before we could disconnect

    print(f"\n--- BLE 결과 ---")
    print(f"  STATUS 수신: {'PASS' if _status_received else 'FAIL (착탈 미감지)'}")
    print(f"  EVENT  수신: {'PASS' if _event_received  else 'FAIL (이벤트 미발생 또는 충격 필요)'}")


async def main():
    print("=" * 50)
    print("BLE 헬멧 모듈 테스트")
    print("=" * 50)
    device = await test_scan()
    if device:
        await test_connect_and_receive(device)


if __name__ == "__main__":
    asyncio.run(main())
