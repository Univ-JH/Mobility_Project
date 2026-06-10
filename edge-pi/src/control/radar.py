import time
import threading
import lgpio

# 사용자님께서 확인해주신 완벽한 하드웨어 핀맵 영구 적용
RADAR_CR_PIN = 4   # 물리 7번 핀 (c/r)
RADAR_DT_PIN = 27  # 물리 13번 핀 (d/t)

class MmwaveRadarSensor:
    def __init__(self):
        self.lock = threading.Lock()
        # 전원 인가 후 센서 안정화 대기 시간
        self._ready_at = time.time() + 2.0
        
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            self.h = lgpio.gpiochip_open(0)
            
        # 노이즈(플로팅) 방지를 위해 SET_PULL_DOWN을 적용하여 입력 모드 설정
        lgpio.gpio_claim_input(self.h, RADAR_CR_PIN, lgpio.SET_PULL_DOWN)
        lgpio.gpio_claim_input(self.h, RADAR_DT_PIN, lgpio.SET_PULL_DOWN)
        print(f"📡 [레이더] 하드웨어 핀 세팅 완료 (c/r: BCM {RADAR_CR_PIN}, d/t: BCM {RADAR_DT_PIN})")

    def get_raw_status(self):
        """디버깅 전용: 센서가 뿜어내는 0과 1이라는 전기 신호를 날것 그대로 반환합니다."""
        with self.lock:
            cr_val = lgpio.gpio_read(self.h, RADAR_CR_PIN)
            dt_val = lgpio.gpio_read(self.h, RADAR_DT_PIN)
            return cr_val, dt_val

    def check_rear_approach(self):
        """메인 시스템 호출용"""
        if time.time() < self._ready_at:
            return False
            
        with self.lock:
            cr_detected = lgpio.gpio_read(self.h, RADAR_CR_PIN) == 1
            dt_detected = lgpio.gpio_read(self.h, RADAR_DT_PIN) == 1
            return cr_detected or dt_detected

    def cleanup(self):
        lgpio.gpio_free(self.h, RADAR_CR_PIN)
        lgpio.gpio_free(self.h, RADAR_DT_PIN)
        lgpio.gpiochip_close(self.h)