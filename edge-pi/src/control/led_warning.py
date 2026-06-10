import threading
import lgpio

try:
    from .control_config import LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN
except ImportError:
    LED_R_PIN = 12
    LED_G_PIN = 13
    LED_B_PIN = 19
    REAR_LED_PIN = 17

PWM_FREQ = 1000

class RearApproachLED:
    def __init__(self):
        self.lock = threading.Lock()
        self._current_state = None  # 상태 캐싱(중복 실행 방지)
        
        try:
            self.h = lgpio.gpiochip_open(4)
        except lgpio.error:
            self.h = lgpio.gpiochip_open(0)
                
        for pin in [LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN]:
            lgpio.gpio_claim_output(self.h, pin)
            
        self.clear()
        print("💡 [LED] 전방 RGB 및 후방 8구 레드바 통합 모듈 준비 완료")

    def _set_rgb_color(self, r_duty, g_duty, b_duty):
        """RGB 색상 제어 (공통 양극 방식 반전)"""
        lgpio.tx_pwm(self.h, LED_R_PIN, PWM_FREQ, 100 - r_duty)
        lgpio.tx_pwm(self.h, LED_G_PIN, PWM_FREQ, 100 - g_duty)
        lgpio.tx_pwm(self.h, LED_B_PIN, PWM_FREQ, 100 - b_duty)

    def update_status(self, brake_level: str, is_rear_approach: bool):
        """메인 루프에서 호출: 브레이크 상태와 후방 감지를 조합하여 LED 표출"""
        new_state = (brake_level, is_rear_approach)
        if self._current_state == new_state:
            return  # 상태가 이전과 같으면 스킵 (과부하 방지)
        
        with self.lock:
            self._current_state = new_state
            
            # 1. 긴급 제동 (최우선)
            if brake_level == "level_emergency":
                self._set_rgb_color(100, 0, 100)          # 전방: 보라색 (위험)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1) # 후방: 레드바 ON
                
            # 2. 일반 브레이크 작동 중
            elif brake_level in ["level_1", "level_2"]:
                self._set_rgb_color(100, 0, 0)            # 전방: 빨강 (제동)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1) # 후방: 레드바 ON
                
            # 3. 주행 중 + 후방 차량 접근
            elif is_rear_approach:
                self._set_rgb_color(100, 70, 0)           # 전방: 주황색 (주의)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 1) # 후방: 레드바 ON
                
            # 4. 평상시 안전 주행
            else:
                self._set_rgb_color(0, 100, 0)            # 전방: 초록색 (안전)
                lgpio.gpio_write(self.h, REAR_LED_PIN, 0) # 후방: 레드바 OFF

    def warn_rear(self):
        """단독 테스트 및 하위 호환용"""
        self.update_status("level_0", True)

    def clear(self):
        self._current_state = None
        with self.lock:
            self._set_rgb_color(0, 0, 0)
            lgpio.gpio_write(self.h, REAR_LED_PIN, 0)

    def cleanup(self):
        self.clear()
        for pin in [LED_R_PIN, LED_G_PIN, LED_B_PIN, REAR_LED_PIN]:
            try:
                lgpio.gpio_free(self.h, pin)
            except Exception:
                pass
        try:
            lgpio.gpiochip_close(self.h)
        except Exception:
            pass
        print("🧹 [LED] 리소스 반환 완료")