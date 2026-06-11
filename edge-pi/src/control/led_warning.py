import time
import threading
import lgpio
from .control_config import LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN

PWM_FREQ = 1000

class RearApproachLED:
    """제동 단계(Brake Level)를 직관적인 색상으로 변환하여 표출하는 지능형 LED 제어 모듈"""

    def __init__(self):
        self.lock = threading.Lock()
        self._current_level = None  # 중복 실행 및 시각 노이즈 방지용 캐싱
        self._active = False        # 구형 main.py 호환용 상태 변수
        
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            self.h = lgpio.gpiochip_open(0)

        for pin in (LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN):
            lgpio.gpio_claim_output(self.h, pin, 0)

        self.clear()
        print("💡 [LED] 제동 단계 연동형 전/후방 경고등(초록/노랑/빨강/보라) 준비 완료")

    def _set_rgb_color(self, r_duty, g_duty, b_duty):
        """전방 RGB LED 색상 제어 (공통 양극 반전 전압 적용)"""
        lgpio.tx_pwm(self.h, LED_R_PIN, PWM_FREQ, 100 - r_duty)
        lgpio.tx_pwm(self.h, LED_G_PIN, PWM_FREQ, 100 - g_duty)
        lgpio.tx_pwm(self.h, LED_B_PIN, PWM_FREQ, 100 - b_duty)

    def update_status(self, brake_level: str):
        """다양한 색상을 표출하는 핵심 지능형 로직"""
        if self._current_level == brake_level:
            return  
            
        with self.lock:
            self._current_level = brake_level
            self._active = True
            
            # 1. 생명 위급 상황 (낙차/충격 사고) -> 전방 보라색 🟣 + 후방 레드바 ON
            if brake_level == "level_emergency":
                self._set_rgb_color(100, 0, 100)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1)
                
            # 2. 강력 제동 상황 -> 전방 빨간색 🔴 + 후방 레드바 ON
            elif brake_level == "level_2":
                self._set_rgb_color(100, 0, 0)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1)
                
            # 3. 감속 주의 상황 -> 전방 노란색 🟡 + 후방 레드바 ON
            elif brake_level == "level_1":
                self._set_rgb_color(100, 60, 0)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1)
                
            # 4. 평상시 정상 주행 -> 전방 초록색 🟢 + 후방 레드바 OFF
            elif brake_level == "level_0":
                self._set_rgb_color(0, 100, 0)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 0)

    # ==========================================================
    # ⚠️ 기존 main.py를 수정하지 않아도 에러가 나지 않도록 지켜주는 호환성 메서드
    # ==========================================================
    def brake_blink(self, count=5, on_ms=100, off_ms=100):
        """급정거 감지 시 후방 LED를 count회 빠르게 깜빡입니다 (자동차 제동등 패턴)."""
        with self.lock:
            for _ in range(count):
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1)
                time.sleep(on_ms / 1000.0)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 0)
                time.sleep(off_ms / 1000.0)

    def warn_rear(self):
        """기존 main.py에서 호출하면 자동으로 '빨간색(위험)' 모드로 전환시킵니다."""
        self.update_status("level_2")

    def clear(self):
        """기존 main.py에서 호출하면 깔끔하게 전체 소등합니다."""
        self._current_level = None
        self._active = False
        with self.lock:
            self._set_rgb_color(0, 0, 0)
            lgpio.gpio_write(self.h, REAR_LED_PIN, 0)

    def cleanup(self):
        self.clear()
        for pin in (LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN):
            try:
                lgpio.gpio_free(self.h, pin)
            except Exception:
                pass
        try:
            lgpio.gpiochip_close(self.h)
        except Exception:
            pass
        print("🧹 [LED] 전후방 경고등 리소스 반환 완료")