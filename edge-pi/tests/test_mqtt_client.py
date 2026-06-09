"""
MQTT 클라이언트 모듈 테스트
- 브로커 연결 확인
- telemetry 페이로드 발행 후 구독으로 수신 검증
- event 페이로드 발행 후 수신 검증

실행: python -m tests.test_mqtt_client  (edge-pi/ 루트에서)
"""
import json
import sys
import os
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.communication.comm_config import (
    MQTT_BROKER, MQTT_PORT, PI_ID,
    MQTT_TOPIC_TELEMETRY, MQTT_TOPIC_EVENT,
)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[SKIP] paho-mqtt 미설치 — pip install paho-mqtt")
    sys.exit(0)

TIMEOUT_SEC = 8

_received = {"telemetry": None, "event": None}
_connected = threading.Event()


MOCK_TELEMETRY = {
    "schemaVersion": 1,
    "deviceId": PI_ID,
    "seq": 9001,
    "rideId": "test-ride-001",
    "timestamp": "2026-01-01T00:00:00",
    "speedKph": 12.5,
    "latitude": 37.5665,
    "longitude": 126.9780,
    "helmet": {"worn": True},
    "health": {"bleConnected": True, "batteryPct": 80},
    "vision": {"surfaceClass": "road", "sidewalkProb": 0.1},
}

MOCK_EVENT = {
    "schemaVersion": 1,
    "deviceId": PI_ID,
    "seq": 9002,
    "rideId": "test-ride-001",
    "timestamp": "2026-01-01T00:00:01",
    "eventType": "sidewalk_detected",
    "severity": "medium",
    "confidence": 0.92,
    "reason": "Test sidewalk event",
    "context": {"speedKph": 12.5, "sidewalkProb": 0.92, "helmetWorn": True},
}


def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("  브로커 연결 성공")
        client.subscribe(MQTT_TOPIC_TELEMETRY)
        client.subscribe(MQTT_TOPIC_EVENT)
        _connected.set()
    else:
        print(f"  ⚠️ 연결 실패 (rc={rc})")


def _on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
        seq = payload.get("seq")
        if topic == MQTT_TOPIC_TELEMETRY and seq == MOCK_TELEMETRY["seq"]:
            _received["telemetry"] = payload
        elif topic == MQTT_TOPIC_EVENT and seq == MOCK_EVENT["seq"]:
            _received["event"] = payload
    except Exception as e:
        print(f"  ⚠️ 메시지 파싱 실패: {e}")


def test_broker_connect():
    print(f"\n[1] 브로커 연결 테스트: {MQTT_BROKER}:{MQTT_PORT}")
    client = mqtt.Client(client_id="test-runner", clean_session=True)
    client.on_connect = _on_connect
    client.on_message = _on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 10)
    except Exception as e:
        print(f"  FAIL — 연결 예외: {e}")
        return None

    client.loop_start()
    connected = _connected.wait(timeout=5.0)
    if not connected:
        print("  FAIL — 연결 타임아웃")
        client.loop_stop()
        return None
    return client


def test_publish_receive(client):
    print(f"\n[2] telemetry 발행/수신 테스트")
    client.publish(MQTT_TOPIC_TELEMETRY, json.dumps(MOCK_TELEMETRY), qos=1)
    deadline = time.time() + TIMEOUT_SEC
    while time.time() < deadline and _received["telemetry"] is None:
        time.sleep(0.1)
    if _received["telemetry"]:
        print(f"  PASS — seq={_received['telemetry']['seq']} 수신 확인")
    else:
        print(f"  FAIL — {TIMEOUT_SEC}초 내 수신 없음")

    print(f"\n[3] event 발행/수신 테스트")
    client.publish(MQTT_TOPIC_EVENT, json.dumps(MOCK_EVENT), qos=1)
    deadline = time.time() + TIMEOUT_SEC
    while time.time() < deadline and _received["event"] is None:
        time.sleep(0.1)
    if _received["event"]:
        print(f"  PASS — seq={_received['event']['seq']} 수신 확인")
    else:
        print(f"  FAIL — {TIMEOUT_SEC}초 내 수신 없음")


def main():
    print("=" * 50)
    print("MQTT 클라이언트 모듈 테스트")
    print("=" * 50)
    client = test_broker_connect()
    if client:
        test_publish_receive(client)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
