# src/communication/mqtt_client.py
import json
import time
import asyncio
from collections import deque
from typing import Dict, Any

# paho-mqtt 라이브러리 필요: pip install paho-mqtt
import paho.mqtt.client as mqtt

from .comm_config import (
    DEVICE_ID, MQTT_BROKER_IP, MQTT_PORT,
    TOPIC_TELEMETRY, TOPIC_EVENT, TOPIC_STATUS
)

class AsyncMQTTClient:
    def __init__(self, ride_id: str):
        self.ride_id = ride_id
        self.client_id = f"edge_pi_{DEVICE_ID}"
        self.client = mqtt.Client(client_id=self.client_id)
        
        # [RULE: 오프라인 대응망] 데이터 유실 방지를 위한 버퍼 큐 (최대 1000개 보관)
        self.event_queue = deque(maxlen=1000)
        self.telemetry_queue = deque(maxlen=1000)
        
        self.is_connected = False

        # MQTT 콜백 등록
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        """연결 성공 시 호출되는 콜백"""
        if rc == 0:
            self.is_connected = True
            print(f"[MQTT] 서버 연결 성공! ({MQTT_BROKER_IP}:{MQTT_PORT})")
            # 연결 시 온라인 상태 알림 (LWT 대신 적극적 발행)
            self._publish_immediate(TOPIC_STATUS, {"status": "ONLINE", "rideId": self.ride_id})
        else:
            print(f"[MQTT] 서버 연결 실패. 반환 코드: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """연결 단절 시 호출되는 콜백"""
        self.is_connected = False
        print(f"[MQTT] 서버 연결 끊어짐! (코드: {rc}) 오프라인 버퍼링 모드로 전환합니다.")

    def _publish_immediate(self, topic: str, payload: Dict[str, Any]):
        """내부 유틸: 메시지를 즉시 전송 시도"""
        try:
            self.client.publish(topic, json.dumps(payload), qos=1)
        except Exception as e:
            print(f"[MQTT_ERR] 전송 실패: {e}")

    async def connect_and_loop(self):
        """[핵심] 비동기 환경에서 MQTT 네트워크 루프와 재연결을 관리"""
        while True:
            if not self.is_connected:
                try:
                    print(f"[MQTT] {MQTT_BROKER_IP}로 연결 시도 중...")
                    self.client.connect(MQTT_BROKER_IP, MQTT_PORT, keepalive=60)
                    self.client.loop_start() # 백그라운드 스레드에서 네트워크 처리 시작
                except Exception as e:
                    print(f"[MQTT] 연결 시도 실패, 5초 후 재시도... : {e}")
                    await asyncio.sleep(5)
                    continue

            # 연결된 상태라면 백그라운드 루프는 돌아가고 있으므로 잠시 대기
            await asyncio.sleep(1)

    def publish_event(self, event_type: str, severity: str, reason: str, details: Dict = None):
        """
        [외부 API] 위험 상황이나 상태 변화 등 중요한 이벤트를 전송 (또는 큐에 적재)
        """
        payload = {
            "deviceId": DEVICE_ID,
            "rideId": self.ride_id,
            "eventType": event_type,
            "severity": severity,
            "reason": reason,
            "timestamp": int(time.time()),
            "details": details or {}
        }

        if self.is_connected:
            self._publish_immediate(TOPIC_EVENT, payload)
        else:
            # [RULE: 오프라인 버퍼링]
            self.event_queue.append(payload)
            print(f"[MQTT_BUFFER] 이벤트 로컬 적재 완료 (큐 크기: {len(self.event_queue)})")

    def publish_telemetry(self, sensor_data: Dict[str, Any], brake_level: str):
        """
        [외부 API] 현재 속도, 배터리, 센서 상태 등 주기적인 텔레메트리 전송
        """
        payload = {
            "deviceId": DEVICE_ID,
            "rideId": self.ride_id,
            "timestamp": int(time.time()),
            "sensors": sensor_data,
            "brakeLevel": brake_level
        }

        if self.is_connected:
            self._publish_immediate(TOPIC_TELEMETRY, payload)
        else:
            # 텔레메트리는 최신 데이터가 중요하므로 큐 크기를 관리하며 적재
            self.telemetry_queue.append(payload)

    async def flush_queues(self):
        """
        [핵심: 오프라인 복구] 연결이 복구되었을 때 버퍼에 쌓인 데이터를 한 번에 전송
        메인 로직에 방해가 되지 않도록 비동기로 동작
        """
        while True:
            if self.is_connected:
                # 1. 이벤트 큐 쏟아내기 (중요도 높음)
                while self.event_queue:
                    payload = self.event_queue.popleft()
                    self._publish_immediate(TOPIC_EVENT, payload)
                    await asyncio.sleep(0.05) # 서버 부하 방지 딜레이

                # 2. 텔레메트리 큐 쏟아내기
                while self.telemetry_queue:
                    payload = self.telemetry_queue.popleft()
                    self._publish_immediate(TOPIC_TELEMETRY, payload)
                    await asyncio.sleep(0.05)

            # 1초마다 큐 검사
            await asyncio.sleep(1)

    def cleanup(self):
        """종료 시 안전하게 연결 해제"""
        if self.is_connected:
            self._publish_immediate(TOPIC_STATUS, {"status": "OFFLINE", "rideId": self.ride_id})
            self.client.loop_stop()
            self.client.disconnect()
            print("[MQTT] 안전하게 종료되었습니다.")