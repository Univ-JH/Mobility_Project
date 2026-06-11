import json
import paho.mqtt.client as mqtt
from datetime import datetime

# 분리된 설정값을 불러옵니다.
from src.communication.comm_config import (
    MQTT_BROKER, MQTT_PORT, MQTT_CLIENT_ID, PI_ID,
    MQTT_TOPIC_TELEMETRY, MQTT_TOPIC_STATUS, MQTT_TOPIC_CONTROL,
)

class BikeMQTTClient:
    def __init__(self):
        # clean_session=False로 설정하여 오프라인 상태에서도 메시지 유실 방지
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID, clean_session=False)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.is_connected = False
        # 서버 제어 명령 수신 콜백 — main.py에서 주입
        # 서명: on_control_command(action: str, payload: dict)
        self.on_control_command = None

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"🌐 [MQTT] AWS 관제 서버 연결 성공!")
            self.is_connected = True
            client.subscribe(MQTT_TOPIC_CONTROL, qos=1)
            print(f"📡 [MQTT] 제어 명령 구독 시작: {MQTT_TOPIC_CONTROL}")
        else:
            print(f"⚠️ [MQTT] 서버 연결 실패 (코드: {rc})")

    def _on_disconnect(self, client, userdata, rc):
        print("❌ [MQTT] 관제 서버 연결 끊김 (오프라인 내부 큐 적재 모드)")
        self.is_connected = False

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            action = payload.get("action", "")
            print(f"📩 [MQTT] 제어 명령 수신: action={action}")
            if self.on_control_command and action:
                self.on_control_command(action, payload)
        except Exception as e:
            print(f"⚠️ [MQTT] 제어 메시지 파싱 실패: {e}")

    def start(self):
        try:
            print(f"🌐 [MQTT] {MQTT_BROKER} 연결 시도 중...")
            # 부팅 시 인터넷이 아직 안 잡혀있어도 에러로 튕기지 않고, 
            # 백그라운드에서 연결될 때까지 자동으로 재시도하도록 동기 connect를 connect_async로 변경합니다.
            self.client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()  # 백그라운드 스레드 시작
        except Exception as e:
            print(f"⚠️ [MQTT] 시작 에러 (네트워크 상태 확인 필요): {e}")

    def send_bike_state(self, speed: float, road_type: str, lat: float, lon: float,
                        arduino_seq: int, is_worn: bool, is_accident: bool,
                        severity: str, reason: str, brake_level: str,
                        confidence: float = 0.5, battery_level: int = -1,
                        helmet_id: str = "unknown"):
        """
        자전거의 모든 센서 및 판단 상태를 하나의 JSON 패킷으로 묶어 서버로 연속 전송합니다.

        confidence: 사고 판단 신뢰도 (0.0~1.0). event_label 기반으로 main.py에서 계산.
        battery_level: 헬멧 배터리 잔량 (%). Arduino 구조체에 미포함 시 -1.
        helmet_id: 연결된 헬멧 BLE MAC 주소. 미연결 시 "unknown".
        """
        payload = {
            "deviceId": PI_ID,                       # Pi 기기 ID
            "helmetId": helmet_id,                   # [CONTRACT-2] 헬멧 BLE MAC 주소
            "speed": round(speed, 2),
            "environment": road_type,
            "latitude": lat,
            "longitude": lon,
            "timestamp": datetime.now().isoformat(),
            "arduino": {
                "seq": arduino_seq,
                "is_worn": is_worn,
                "is_accident": is_accident,
                "battery_level": battery_level,      # [CONTRACT-1] -1 = 아두이노 미전송 (구조체 미포함)
            },
            "safety": {
                "severity": severity,
                "reason": reason,
                "brake_level": brake_level,
                "confidence": round(confidence, 3),  # [CONTRACT-3] 사고 판단 신뢰도
            }
        }

        # 오프라인 상태이거나 위험도가 높을 때 데이터 유실을 막기 위해 QoS 1 사용
        qos_level = 1
        self.client.publish(MQTT_TOPIC_TELEMETRY, json.dumps(payload), qos=qos_level)

    def send_helmet_status(self, connected: bool, helmet_id: str):
        """[BUG-J] 헬멧 BLE 연결/끊김 상태를 device/{id}/status 토픽으로 발행.
        백엔드가 헬멧 connectivity를 추적하는 데 사용.
        """
        payload = {
            "deviceId":        PI_ID,
            "helmetId":        helmet_id,
            "helmet_connected": connected,
            "timestamp":       datetime.now().isoformat(),
        }
        self.client.publish(MQTT_TOPIC_STATUS, json.dumps(payload), qos=1)
        state = "연결" if connected else "끊김"
        print(f"[MQTT] 헬멧 상태 발행: {state} (helmet_id={helmet_id})")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("🧹 [MQTT] 통신 클라이언트 종료")