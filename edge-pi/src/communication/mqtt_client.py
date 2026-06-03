import json
import paho.mqtt.client as mqtt
from datetime import datetime

# 분리된 설정값을 불러옵니다.
from src.communication.comm_config import (
    MQTT_BROKER, MQTT_PORT, MQTT_CLIENT_ID, MQTT_TOPIC_TELEMETRY
)

class BikeMQTTClient:
    def __init__(self):
        # clean_session=False로 설정하여 오프라인 상태에서도 메시지 유실 방지
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID, clean_session=False)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.is_connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"🌐 [MQTT] AWS 관제 서버 연결 성공!")
            self.is_connected = True
        else:
            print(f"⚠️ [MQTT] 서버 연결 실패 (코드: {rc})")

    def _on_disconnect(self, client, userdata, rc):
        print("❌ [MQTT] 관제 서버 연결 끊김 (오프라인 내부 큐 적재 모드)")
        self.is_connected = False

    def start(self):
        try:
            print(f"🌐 [MQTT] {MQTT_BROKER} 연결 시도 중...")
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()  # 백그라운드 스레드 시작
        except Exception as e:
            print(f"⚠️ [MQTT] 시작 에러: {e}")

    # ★ 인자 이름 변경: brake_level -> brake_action
    def send_bike_state(self, speed: float, road_type: str, lat: float, lon: float, 
                        arduino_seq: int, is_worn: bool, is_accident: bool, 
                        severity: str, reason: str, brake_action: str):
        """
        자전거의 모든 센서 및 판단 상태를 하나의 JSON 패킷으로 묶어 서버로 연속 전송합니다.
        """
        # NoSQL 기반 JSON 구조 설계
        payload = {
            "deviceId": MQTT_CLIENT_ID,       # 1. 기기 아이디 (pi_01)
            "speed": round(speed, 2),         # 2. 현재 속도 (km/h)
            "environment": road_type,         # 3. 주행 노면 (road / sidewalk)
            "latitude": lat,                  # 4. 위도
            "longitude": lon,                 # 5. 경도
            "timestamp": datetime.now().isoformat(), # 6. 데이터 발생 시간
            "arduino": {
                "seq": arduino_seq,           # 7. 아두이노 패킷 번호
                "is_worn": is_worn,           # 8. 헬멧 착용 여부
                "is_accident": is_accident     # 9. 헬멧 사고 여부
            },
            "safety": {
                "severity": severity,         # 10. 위험도 (NONE / INFO / WARNING / CRITICAL)
                "reason": reason,             # 11. 브레이크 작동 이유
                "brake_action": brake_action  # 12. 브레이크 제어 액션 (BRAKE_ENGAGE / NORMAL 등)
            }
        }

        # 오프라인 상태이거나 위험도가 높을 때 데이터 유실을 막기 위해 QoS 1 사용
        qos_level = 1
        self.client.publish(MQTT_TOPIC_TELEMETRY, json.dumps(payload), qos=qos_level)

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("🧹 [MQTT] 통신 클라이언트 종료")