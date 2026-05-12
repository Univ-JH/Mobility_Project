import json
import paho.mqtt.client as mqtt
from datetime import datetime

from src.communication.comm_config import (
    MQTT_BROKER, MQTT_PORT, MQTT_CLIENT_ID, 
    MQTT_TOPIC_EVENT, MQTT_TOPIC_EMERGENCY, MQTT_TOPIC_TELEMETRY
)

class BikeMQTTClient:
    def __init__(self):
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID, clean_session=False)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.is_connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"🌐 [MQTT] 관제 서버 연결 성공!")
            self.is_connected = True
        else:
            print(f"⚠️ [MQTT] 서버 연결 실패 (코드: {rc})")

    def _on_disconnect(self, client, userdata, rc):
        print("❌ [MQTT] 관제 서버 연결 끊김 (큐 적재 모드 전환)")
        self.is_connected = False

    def start(self):
        try:
            print(f"🌐 [MQTT] {MQTT_BROKER} 연결 시도 중...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()  
        except Exception as e:
            print(f"⚠️ [MQTT] 시작 에러: {e}")

    def send_event(self, event_type, severity, payload):
        data = {
            "deviceId": MQTT_CLIENT_ID,
            "eventType": event_type,
            "severity": severity,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }
        self.client.publish(MQTT_TOPIC_EVENT, json.dumps(data), qos=1)

    def send_emergency(self, is_worn, speed, status="PENDING"):
        data = {
            "deviceId": MQTT_CLIENT_ID,
            "helmet_worn": is_worn,
            "speed": speed,
            "status": status,
            "message": "긴급 사고 발생 감지!",
            "timestamp": datetime.now().isoformat()
        }
        self.client.publish(MQTT_TOPIC_EMERGENCY, json.dumps(data), qos=2) 
        if self.is_connected:
            print(f"🚨 [MQTT] 긴급 사고 알림 전송 완료!")

    def send_telemetry(self, speed, battery_level=100, road_type="road"):
        if not self.is_connected: return 
        
        data = {
            "deviceId": MQTT_CLIENT_ID,
            "speed": speed,
            "battery": battery_level,
            "environment": road_type,
            "timestamp": datetime.now().isoformat()
        }
        self.client.publish(MQTT_TOPIC_TELEMETRY, json.dumps(data), qos=0)

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("🧹 [MQTT] 통신 클라이언트 종료")