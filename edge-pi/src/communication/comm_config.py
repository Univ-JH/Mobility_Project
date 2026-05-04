import os

# --- Device & BLE Settings ---
DEVICE_ID = os.getenv("DEVICE_ID", "PI-5-BUSAN-01")
HELMET_MAC_ADDR = os.getenv("HELMET_MAC_ADDR", "AA:BB:CC:DD:EE:FF")

# 아두이노 Nano 33 BLE 특성 UUID (실제 아두이노 코드와 맞춰야 함)
BLE_CHAR_DATA_UUID = "00002A5D-0000-1000-8000-00805f9b34fb"

# 연결 정책
BLE_RECONNECT_INTERVAL = 3.0  # 끊김 시 재연결 대기 시간 (초)
BLE_SCAN_TIMEOUT = 10.0       # 장치 스캔 최대 대기 시간