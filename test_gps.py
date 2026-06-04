import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime, timezone

# AWS 서버 IP 주소
MQTT_BROKER = "52.79.242.44"
MQTT_PORT = 1883
# 백엔드가 수신하는 토픽으로 변경 (device/pi_01/telemetry)
TOPIC = "device/pi_01/telemetry"

# 초기 시작 위치 (강남역 부근)
BASE_LAT = 35.15905
BASE_LON = 129.0372

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("AWS MQTT Broker 연결 성공!")
    else:
        print(f"연결 실패, 에러 코드: {reason_code}")

def send_mock_gps():
    # paho-mqtt v2.0 호환성 해결
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "mock_gps_sender")
    except AttributeError:
        # 구버전 paho-mqtt 처리
        client = mqtt.Client("mock_gps_sender")
        
    client.on_connect = on_connect
    
    print(f"📡 AWS 서버({MQTT_BROKER})로 접속 시도 중...")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        print(f"연결 에러: {e}")
        return
        
    client.loop_start()
    
    seq = 0
    print("🚗 가상의 자전거가 이동을 시작합니다! (Ctrl+C를 눌러 종료하세요)")
    
    while True:
        # 북동쪽으로 조금씩 이동하도록 좌표 수정 (약 10m씩 이동)
        lat = BASE_LAT + (seq * 0.0001)
        lon = BASE_LON + (seq * 0.0001)
        
        payload = {
            "schemaVersion": 1,
            "deviceId": "pi_01",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seq": seq,
            "rideId": "test_ride_001",
            "latitude": lat,
            "longitude": lon,
            "helmet": {"worn": True},
            "health": {"bleConnected": True, "batteryPct": 90}
        }
        
        msg = json.dumps(payload)
        client.publish(TOPIC, msg, qos=1)
        print(f"📍 GPS 전송! [Seq:{seq}] ➡️ 위도: {lat:.6f}, 경도: {lon:.6f}")
        
        seq += 1
        time.sleep(5)  # 프론트엔드가 지도에서 자연스럽게 움직이는 걸 보기 위해 5초 대기

if __name__ == "__main__":
    try:
        send_mock_gps()
    except KeyboardInterrupt:
        print("\n🛑 테스트 송신을 종료합니다.")
