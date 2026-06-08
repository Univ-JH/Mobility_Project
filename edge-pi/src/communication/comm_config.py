# ==========================================
# [0] 기기 고유 식별 번호 (Numbering)
# ==========================================
PI_ID = "pi_01" 

# ==========================================
# [1] BLE (블루투스) 헬멧 통신 설정 (구조체 버전)
# ==========================================
BLE_DEVICE_NAME = "SmartHelmet_Alpha"

# GATT 서비스 UUID (헬멧 서비스 루트)
SERVICE_UUID      = "19B10000-E8F2-537E-4F6C-D104768A1214"

# Characteristic UUID — Arduino → Pi (Read | Notify)
STATUS_CHAR_UUID  = "19B10001-E8F2-537E-4F6C-D104768A1214"  # 착용 상태 (1 byte)
EVENT_CHAR_UUID   = "19B10002-E8F2-537E-4F6C-D104768A1214"  # 안전 이벤트 (14 bytes)

# 아두이노 C++ 구조체 데이터 규격 (총 14바이트)
# < (리틀엔디안) / B (1바이트) / I (4바이트 정수)
EVENT_STRUCT_FORMAT = "<BIIIB"

# ==========================================
# [2] MQTT (AWS 관제 서버) 통신 설정
# ==========================================
MQTT_BROKER = "52.79.242.44"  # [수정 필요] AWS EC2 퍼블릭 IP 주소 입력
MQTT_PORT = 1883

# 클라이언트 ID 자동 생성 (예: alpha_node_pi_01)
MQTT_CLIENT_ID = f"alpha_node_{PI_ID}"

# ==========================================
# [3] MQTT 발행(Publish) 토픽 설정
# 백엔드가 수신하는 토픽 규격(device/+/telemetry)에 맞춤
# ==========================================
MQTT_TOPIC_TELEMETRY = f"device/{PI_ID}/telemetry"
MQTT_TOPIC_EVENT     = f"device/{PI_ID}/event"
MQTT_TOPIC_STATUS    = f"device/{PI_ID}/status"    # 헬멧 BLE 연결/끊김 상태 [BUG-J]
MQTT_TOPIC_EMERGENCY = f"device/{PI_ID}/emergency"

# ==========================================
# [4] GPS / IMU 설정
# ==========================================
GPS_SERIAL_PORT = "/dev/ttyAMA0"
GPS_BAUDRATE = 9600
IMU_I2C_ADDRESS = 0x68
IMU_SHOCK_THRESHOLD = 2.0

# ==========================================
# [5] AI 비전 (도로/인도 판별) 통신 설정
# ==========================================
VISION_HOST = "127.0.0.1"  # 라즈베리 파이 내부 통신
VISION_PORT = 5005

# AI 스크립트에서 보내줄 문자열 규격
AI_ROAD_VAL = "1"
AI_SIDEWALK_VAL = "0"

# 시스템 내부에서 사용할 명칭
CLASS_ROAD = "road"
CLASS_SIDEWALK = "sidewalk"

# ==========================================
# [6] 백엔드 HTTP 설정 (heartbeat용)
# ==========================================
BACKEND_URL = "http://52.79.242.44:8000"
PRE_SHARED_TOKEN = "proto-secret-token-123"