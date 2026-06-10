import time
import threading
import lgpio

try:
    from .control_config import RADAR_CR_PIN, RADAR_DT_PIN
except ImportError:
    RADAR_CR_PIN = 4
    RADAR_DT_PIN = 27

class MmwaveRadarSensor:
    def __init__(self):
        self.lock = threading.Lock()
        # 웜업 시간 (전원이 켜지고 전파가 안정화되는 시간 2초 대기)
        self._ready_at = time.time() + 2.0
        
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            self.h = lgpio.gpiochip_open(0)
            
        # CR(근거리)과 DT(원거리) 핀 모두 입력(Input) 모드로 설정
        lgpio.gpio_claim_input(self.h, RADAR_CR_PIN, lgpio.SET_PULL_DOWN)
        lgpio.gpio_claim_input(self.h, RADAR_DT_PIN, lgpio.SET_PULL_DOWN)
        print(f"📡 [레이더] mmWave 초기화 완료 (근거리 핀:{RADAR_CR_PIN}, 원거리 핀:{RADAR_DT_PIN})")

    def check_rear_approach(self):
        """메인 시스템에서 호출: 원거리/근거리 어디든 걸리면 True 반환 (감지 거리 확장)"""
        if time.time() < self._ready_at:
            return False
            
        with self.lock:
            cr_detected = lgpio.gpio_read(self.h, RADAR_CR_PIN) == 1
            dt_detected = lgpio.gpio_read(self.h, RADAR_DT_PIN) == 1
            
            # 둘 중 하나라도 걸리면 접근으로 판단!
            return cr_detected or dt_detected

    def get_detailed_status(self):
        """테스트 전용: 근거리, 원거리 핀이 각각 어떤 상태인지 상세 반환"""
        if time.time() < self._ready_at:
            return False, False
            
        with self.lock:
            cr_detected = lgpio.gpio_read(self.h, RADAR_CR_PIN) == 1
            dt_detected = lgpio.gpio_read(self.h, RADAR_DT_PIN) == 1
            return cr_detected, dt_detected

    def cleanup(self):
        lgpio.gpio_free(self.h, RADAR_CR_PIN)
        lgpio.gpio_free(self.h, RADAR_DT_PIN)
        lgpio.gpiochip_close(self.h)
        print("🧹 [레이더] 리소스 안전 반환 완료")