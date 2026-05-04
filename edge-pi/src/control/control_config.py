# --- GPIO Pin Settings (BCM numbering) ---
ULTRASONIC_TRIG = 23    # HY-SRF05 Trigger 핀 (초음파 발사)
ULTRASONIC_ECHO = 24    # HY-SRF05 Echo 핀 (초음파 수신)

# --- Ultrasonic Parameters ---
SOUND_SPEED = 34300     # 음속 (cm/s)
TIMEOUT_LIMIT = 0.02    # 에코 수신 대기 타임아웃 (약 3.4m 범위) - 안전장치, 0.02초까지만 기다리고, 그 후에는 오류로 처리

# --- Safety Thresholds ---
DISTANCE_MIN_THRESHOLD = 2.0   # 최소 감지 거리 (cm)
DISTANCE_MAX_THRESHOLD = 400.0 # 최대 감지 거리 (cm)

# --- 서보 모터(Brake) 핀 및 PWM 설정 ---
SERVO_PIN = 18          # RDS-3218 제어 신호(노란선) 연결 핀 (BCM 18)
SERVO_MIN_PULSE = 500   # 0도에 해당하는 펄스폭 (us)
SERVO_MAX_PULSE = 2500  # 180도에 해당하는 펄스폭 (us)

# --- 제동 레벨 캘리브레이션 (각도: 0 ~ 180) ---
# 물리적 브레이크 설계에 따라 테스트 후 이 각도
BRAKE_LEVELS = {
    "level_0": 0,       # 브레이크 완전 해제 (정상 주행)
    "level_1": 45,      # 약한 제동 (감속)
    "level_2": 90,      # 강한 제동 (급감속)
    "level_emergency": 135 # 긴급 제동 (최대 토크)
}