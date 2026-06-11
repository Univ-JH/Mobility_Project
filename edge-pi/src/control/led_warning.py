import threading
import lgpio
from .control_config import LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN

PWM_FREQ = 1000

class RearApproachLED:
    """제동 단계(Brake Level)를 직관적인 색상으로 변환하여 표출하는 지능형 LED 제어 모듈"""

    def __init__(self):
        self.lock = threading.Lock()
        self._current_level = None  # 중복 실행 및 시각 노이즈 방지용 캐싱
        
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            self.h = lgpio.gpiochip_open(0)

        for pin in (LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN):
            lgpio.gpio_claim_output(self.h, pin, 0)

        self.clear()
        print("💡 [LED] 제동 단계 연동형 전/후방 경고등 준비 완료")

    def _set_rgb_color(self, r_duty, g_duty, b_duty):
        """전방 RGB LED 색상 제어 (공통 양극 반전 전압 적용)"""
        lgpio.tx_pwm(self.h, LED_R_PIN, PWM_FREQ, 100 - r_duty)
        lgpio.tx_pwm(self.h, LED_G_PIN, PWM_FREQ, 100 - g_duty)
        lgpio.tx_pwm(self.h, LED_B_PIN, PWM_FREQ, 100 - b_duty)

    def update_status(self, brake_level: str):
        """main.py에서 호출: 브레이크 단계에 매핑된 색상과 후방 레드바를 제어합니다."""
        if self._current_level == brake_level:
            return  # 이전과 같은 상태면 하드웨어 통신을 건너뜁니다.
            
        with self.lock:
            self._current_level = brake_level
            
            # 1. 생명 위급 상황 (낙차/충격 사고) -> 전방 보라색 🟣 + 후방 레드바 ON
            if brake_level == "level_emergency":
                self._set_rgb_color(100, 0, 100)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1)
                print("🟣 [LED] 긴급 상황 경고 (보라색 점등)")
                
            # 2. 강력 제동 상황 (인도 진입 위험 등) -> 전방 빨간색 🔴 + 후방 레드바 ON
            elif brake_level == "level_2":
                self._set_rgb_color(100, 0, 0)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1)
                print("🔴 [LED] 위험 제동 경고 (빨간색 점등)")
                
            # 3. 감속 주의 상황 (주의 단계 브레이크) -> 전방 노란색 🟡 + 후방 레드바 ON
            elif brake_level == "level_1":
                self._set_rgb_color(100, 60, 0)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1)
                print("🟡 [LED] 감속 주행 주의 (노란색 점등)")
                
            # 4. 평상시 정상 주행 -> 전방 초록색 🟢 + 후방 레드바 OFF 🌑
            else:
                self._set_rgb_color(0, 100, 0)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 0)

    @property
    def _active(self):
        return self._current_level is not None

    def warn_rear(self):
        """테스트용: 경고 점등 (앞 빨강 + 후방 레드바 ON). 중복 호출 무시."""
        if self._active:
            return
        self.update_status("level_2")

    def test_colors(self):
        """테스트용: 전방 RGB 색상 순차 확인."""
        import time
        with self.lock:
            print("  → 전방: 초록색 켜짐")
            self._set_rgb_color(0, 100, 0)
            time.sleep(1.5)
            print("  → 전방: 노란색 켜짐")
            self._set_rgb_color(100, 70, 0)
            time.sleep(1.5)
            self._set_rgb_color(0, 0, 0)

    def test_rear_only(self):
        """테스트용: 후방 8구 레드바 단독 점등 확인."""
        import time
        with self.lock:
            print(f"  → 후방 레드바 ON (핀: {REAR_LED_PIN})")
            lgpio.gpio_write(self.h, REAR_LED_PIN, 1)
            time.sleep(2.0)
            print("  → 후방 레드바 OFF")
            lgpio.gpio_write(self.h, REAR_LED_PIN, 0)

    def clear(self):
        """모든 LED 소등"""
        self._current_level = None
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